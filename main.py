import socket
from config import UDP_IP, UDP_PORT, CTY_FILE, CONFIRMED_FILE
from wsjtx.decoder import parse_decode
from dxcc.callsign import extract_dx_call
from dxcc.cty_parser import load_cty, get_country, clean_country
from notify.windows import notify_new_dxcc

def load_confirmed(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def main():
    prefixes = load_cty(CTY_FILE)
    confirmed = load_confirmed(CONFIRMED_FILE)
    print(confirmed)
    alerted = set()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"Listening UDP {UDP_IP}:{UDP_PORT}...")

    try:
        while True:

            data, _ = sock.recvfrom(2048)

            decoded = parse_decode(data)
            if not decoded:
                continue

            call = extract_dx_call(decoded["message"])
            if not call:
                continue

            country = get_country(call, prefixes)

            if not country or country in confirmed:
                continue

            key = f"{call}:{country}"
            if key in alerted:
                continue

            alerted.add(key)

            print(f"NEW DXCC: {country} ({call})")
            notify_new_dxcc(country, call, decoded["mode"], decoded["snr"])
    except KeyboardInterrupt:
            print("\nStopping DXCC watcher...")
    finally:
            sock.close()

if __name__ == "__main__":
    main()
