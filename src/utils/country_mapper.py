from typing import Dict

# Note: Brazil uses mercadolivre.com.br
COUNTRY_TO_DOMAIN: Dict[str, str] = {
    "ar": "https://www.mercadolibre.com.ar",
    "bo": "https://www.mercadolibre.com.bo",
    "br": "https://www.mercadolivre.com.br",
    "cl": "https://www.mercadolibre.cl",
    "co": "https://www.mercadolibre.com.co",
    "cr": "https://www.mercadolibre.co.cr",
    "do": "https://www.mercadolibre.com.do",
    "ec": "https://www.mercadolibre.com.ec",
    "gt": "https://www.mercadolibre.com.gt",
    "hn": "https://www.mercadolibre.com.hn",
    "mx": "https://www.mercadolibre.com.mx",
    "ni": "https://www.mercadolibre.com.ni",
    "pa": "https://www.mercadolibre.com.pa",
    "py": "https://www.mercadolibre.com.py",
    "pe": "https://www.mercadolibre.com.pe",
    "sv": "https://www.mercadolibre.com.sv",
    "uy": "https://www.mercadolibre.com.uy",
    "ve": "https://www.mercadolibre.com.ve",
}

COUNTRY_TO_CURRENCY: Dict[str, str] = {
    "ar": "ARS",
    "bo": "BOB",
    "br": "BRL",
    "cl": "CLP",
    "co": "COP",
    "cr": "CRC",
    "do": "DOP",
    "ec": "USD",
    "gt": "GTQ",
    "hn": "HNL",
    "mx": "MXN",
    "ni": "NIO",
    "pa": "PAB",
    "py": "PYG",
    "pe": "PEN",
    "sv": "USD",
    "uy": "UYU",
    "ve": "VES",
}

def normalize_country_or_url(raw: str) -> str:
    """
    Accepts:
      - Full URL (returned unchanged)
      - 'mx:/p/MLM12345'  -> https://www.mercadolibre.com.mx/p/MLM12345
      - 'br:/produto/...' -> https://www.mercadolivre.com.br/produto/...
    """
    raw = raw.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if ":" in raw:
        country, path = raw.split(":", 1)
        country = country.lower()
        base = COUNTRY_TO_DOMAIN.get(country)
        if not base:
            raise ValueError(f"Unsupported country code: {country}")
        path = path if path.startswith("/") else f"/{path}"
        return f"{base}{path}"
    # If someone passed just a country code, default to homepage
    if len(raw) == 2:
        base = COUNTRY_TO_DOMAIN.get(raw.lower())
        if base:
            return base
    # Otherwise assume it's a raw path for MX
    return f"{COUNTRY_TO_DOMAIN['mx']}{raw if raw.startswith('/') else '/' + raw}"