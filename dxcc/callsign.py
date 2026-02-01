import re

CALL_RE = re.compile(r"^[A-Z0-9/]{3,}$")

def extract_dx_call(message: str) -> str | None:
    parts = message.split()

    if not parts:
        return None

    if parts[0] == "CQ":
        if len(parts) >= 2 and CALL_RE.match(parts[1]):
            return parts[1]
        return None

    if len(parts) >= 2 and CALL_RE.match(parts[1]):
        return parts[1]

    return None
