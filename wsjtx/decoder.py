import struct

MAGIC = 0xADBCCBDA
MSG_DECODE = 2

def read_string(data, offset):
    length = struct.unpack(">I", data[offset:offset+4])[0]
    offset += 4
    value = data[offset:offset+length].decode("utf-8", errors="ignore")
    offset += length
    return value, offset


def parse_decode(data):
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
    offset += 1
    offset += 4
    snr = struct.unpack(">i", data[offset:offset+4])[0]
    offset += 4
    offset += 8
    offset += 4
    mode, offset = read_string(data, offset)
    message, offset = read_string(data, offset)

    return {
        "mode": mode,
        "snr": snr,
        "message": message,
    }
