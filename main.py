"""
Author: Alexander Zahrebaiev
Callsign: UW5EMC
Email: lulzsecer@gmail.com
Website: https://devtech.dp.ua/
Date: 2026-02-01
Version: 1.1
"""
import socket
from config import UDP_IP, UDP_PORT, CTY_FILE, CONFIRMED_FILES, CONFIRMED_FILE_DEFAULT
from wsjtx.decoder import parse_decode, parse_status
from dxcc.callsign import extract_dx_call
from dxcc.cty_parser import load_cty, get_country, clean_country
from notify.windows import notify_new_dxcc

def load_confirmed(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def get_confirmed_for_band(band):
    if band and band in CONFIRMED_FILES:
        return load_confirmed(CONFIRMED_FILES[band])
    return load_confirmed(CONFIRMED_FILE_DEFAULT)

def main():
    prefixes = load_cty(CTY_FILE)
    alerted = set()

    current_frequency = None
    current_band = None
    confirmed = set()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"Listening UDP {UDP_IP}:{UDP_PORT}...")

    try:
        while True:
            data, _ = sock.recvfrom(8192)

            # STATUS ?
            status = parse_status(data)
            if status:
                new_frequency = status.get("frequency")
                new_band = status.get("band")


                if new_band != current_band:
                    current_band = new_band
                    current_frequency = new_frequency
                    confirmed = get_confirmed_for_band(current_band)
                    print(f"Band changed to: {current_band or 'unknown'} ({current_frequency/1e6:.3f} MHz)")
                    print(f"Loaded {len(confirmed)} confirmed countries for this band")
                    # alerted.clear()
                else:
                    current_frequency = new_frequency
                continue

            #  DECODE
            decoded = parse_decode(data, current_frequency)
            if not decoded:
                continue

            call = extract_dx_call(decoded["message"])
            if not call:
                continue

            country = get_country(call, prefixes)

            if not country or country in confirmed:
                continue


            key = f"{current_band}:{call}:{country}"
            if key in alerted:
                continue

            alerted.add(key)

            band_info = f"[{current_band}]" if current_band else ""
            freq_info = f"{decoded.get('frequency_mhz', 0):.3f} MHz" if decoded.get('frequency_mhz') else ""

            print(f"NEW DXCC {band_info}: {country} ({call}) - {freq_info}")
            notify_new_dxcc(country, call, decoded["mode"], decoded["snr"])

    except KeyboardInterrupt:
        print("\nStopping DXCC watcher...")
    finally:
        sock.close()

if __name__ == "__main__":
    main()