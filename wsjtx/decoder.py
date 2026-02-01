import struct

MAGIC = 0xADBCCBDA
MSG_STATUS = 1
MSG_DECODE = 2


def read_string(data, offset):

    if offset + 4 > len(data):
        return "", offset
    length = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4
    if offset + length > len(data):
        return "", offset
    value = data[offset:offset + length].decode("utf-8", errors="ignore")
    offset += length
    return value, offset


def read_bool(data, offset):

    if offset + 1 > len(data):
        return False, offset
    value = struct.unpack(">?", data[offset:offset + 1])[0]
    return value, offset + 1


def get_band(frequency_hz):
    freq_mhz = frequency_hz / 1e6

    if 1.8 <= freq_mhz < 2.0:
        return "160m"
    elif 3.5 <= freq_mhz < 4.0:
        return "80m"
    elif 5.3 <= freq_mhz < 5.4:
        return "60m"
    elif 7.0 <= freq_mhz < 7.3:
        return "40m"
    elif 10.1 <= freq_mhz < 10.15:
        return "30m"
    elif 14.0 <= freq_mhz < 14.35:
        return "20m"
    elif 18.068 <= freq_mhz < 18.168:
        return "17m"
    elif 21.0 <= freq_mhz < 21.45:
        return "15m"
    elif 24.89 <= freq_mhz < 24.99:
        return "12m"
    elif 28.0 <= freq_mhz < 29.7:
        return "10m"
    elif 50.0 <= freq_mhz < 54.0:
        return "6m"
    elif 144.0 <= freq_mhz < 148.0:
        return "2m"
    elif 222.0 <= freq_mhz < 225.0:
        return "1.25m"
    elif 420.0 <= freq_mhz < 450.0:
        return "70cm"
    else:
        return None


def parse_decode(data, frequency=None):

    if len(data) < 12:
        return None

    magic = struct.unpack(">I", data[0:4])[0]
    if magic != MAGIC:
        return None

    msg_type = struct.unpack(">I", data[8:12])[0]
    if msg_type != MSG_DECODE:
        return None

    offset = 12
    wsjtx_id, offset = read_string(data, offset)

    # New (bool)
    offset += 1

    # Time (u32)
    offset += 4

    # SNR (i32)
    if offset + 4 > len(data):
        return None
    snr = struct.unpack(">i", data[offset:offset + 4])[0]
    offset += 4

    # Delta time (f64)
    offset += 8

    # Delta frequency (u32)
    if offset + 4 > len(data):
        return None
    delta_freq = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4

    # Mode (QString)
    mode, offset = read_string(data, offset)

    # Message (QString)
    message, offset = read_string(data, offset)

    result = {
        "mode": mode,
        "snr": snr,
        "delta_freq": delta_freq,
        "message": message,
    }


    if frequency is not None:
        full_freq = frequency + delta_freq
        result["frequency"] = full_freq
        result["frequency_mhz"] = full_freq / 1e6
        result["band"] = get_band(full_freq)

    return result

def parse_status(data):
    if len(data) < 12:
        return None

    magic = struct.unpack(">I", data[0:4])[0]
    if magic != MAGIC:
        return None

    msg_type = struct.unpack(">I", data[8:12])[0]
    if msg_type != MSG_STATUS:
        return None

    offset = 12
    wsjtx_id, offset = read_string(data, offset)


    if offset + 8 > len(data):
        return None
    frequency = struct.unpack(">Q", data[offset:offset + 8])[0]
    offset += 8

    mode, offset = read_string(data, offset)
    dx_call, offset = read_string(data, offset)
    report, offset = read_string(data, offset)
    tx_mode, offset = read_string(data, offset)
    tx_enabled, offset = read_bool(data, offset)
    transmitting, offset = read_bool(data, offset)
    decoding, offset = read_bool(data, offset)

    # RX DF (u32)
    if offset + 4 <= len(data):
        rx_df = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
    else:
        rx_df = 0

    # TX DF (u32)
    if offset + 4 <= len(data):
        tx_df = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
    else:
        tx_df = 0

    de_call, offset = read_string(data, offset)
    de_grid, offset = read_string(data, offset)
    dx_grid, offset = read_string(data, offset)

    return {
        "type": "STATUS",
        "wsjtx_id": wsjtx_id,
        "frequency": frequency,
        "frequency_mhz": frequency / 1e6,
        "band": get_band(frequency),
        "mode": mode,
        "dx_call": dx_call,
        "report": report,
        "tx_mode": tx_mode,
        "tx_enabled": tx_enabled,
        "transmitting": transmitting,
        "decoding": decoding,
        "rx_df": rx_df,
        "tx_df": tx_df,
        "de_call": de_call,
        "de_grid": de_grid,
        "dx_grid": dx_grid
    }