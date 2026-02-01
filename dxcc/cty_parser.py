import re


def load_cty(filename):
    prefixes = []
    country = None

    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # если строка заканчивается на :, убираем двоеточие
            if line.endswith(":"):
                country = line[:-1].strip()
                continue

            for p in line.replace(";", "").split(","):
                p = p.strip()
                if p:
                    prefixes.append((p, country))

    prefixes.sort(key=lambda x: len(x[0]), reverse=True)
    return prefixes

def get_country(callsign, prefixes):
    call = callsign.upper()
    for prefix, country in prefixes:
        if call.startswith(prefix):
            country = clean_country(country)
            country = country.replace(":", "")
            country = country.strip()
            country = country.upper()
            return country
    return None

def clean_country(raw_country):
    if not raw_country:
        return None
    country = raw_country.split(":")[0].strip()
    return country.upper()