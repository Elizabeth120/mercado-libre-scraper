import json
import logging
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from .seller_parser import extract_seller_from_soup

logger = logging.getLogger(__name__)

def _first_str(x) -> Optional[str]:
    if isinstance(x, list):
        for item in x:
            if isinstance(item, str) and item.strip():
                return item.strip()
    if isinstance(x, str):
        s = x.strip()
        return s if s else None
    return None

def _to_int_safe(value: Any) -> Optional[int]:
    try:
        return int(re.sub(r"[^\d]", "", str(value)))
    except Exception:
        return None

def _to_float_safe(value: Any) -> Optional[float]:
    try:
        # keep dot and comma; replace thousand separators
        cleaned = re.sub(r"[^\d,\.]", "", str(value))
        # If both comma and dot present, assume comma is thousand sep -> remove commas
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        # If only comma present, treat as decimal
        elif "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(",", ".")
        return float(cleaned)
    except Exception:
        return None

def _parse_ldjson_product(soup: BeautifulSoup) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            # Some pages include multiple JSON objects; normalize into list
            raw = json.loads(tag.string or "{}")
            blocks = raw if isinstance(raw, list) else [raw]
            for b in blocks:
                if isinstance(b, dict) and b.get("@type") in {"Product", "SoftwareApplication"}:
                    data = b
                    return data
        except Exception:
            continue
    return data

def _images_from_soup(soup: BeautifulSoup) -> List[str]:
    imgs: List[str] = []
    # Try ld+json first
    ld = _parse_ldjson_product(soup)
    if ld:
        images = ld.get("image")
        if isinstance(images, list):
            imgs.extend([u for u in images if isinstance(u, str)])
        elif isinstance(images, str):
            imgs.append(images)

    # Fallback to gallery selectors
    for sel in [
        "img.ui-pdp-image",
        ".ui-pdp-gallery__wrapper img",
        "figure img",
        "img[src*='mlstatic.com']",
    ]:
        for img in soup.select(sel):
            src = img.get("src") or img.get("data-src")
            if src and src not in imgs:
                imgs.append(src)
    # Deduplicate while preserving order
    seen = set()
    dedup = []
    for u in imgs:
        if u not in seen:
            dedup.append(u)
            seen.add(u)
    return dedup[:20]

def parse_product(html: str, url: str) -> Dict[str, Any]:
    """
    Parse a MercadoLibre product HTML page into a normalized dictionary.
    Robust to regional site differences by preferring JSON-LD when present.
    """
    soup = BeautifulSoup(html, "lxml")

    ld = _parse_ldjson_product(soup)

    # Title
    title = None
    if ld:
        title = _first_str(ld.get("name"))
    if not title:
        node = soup.select_one("h1.ui-pdp-title") or soup.find("h1")
        title = node.get_text(strip=True) if node else None

    # Price & Currency
    price = None
    currency = None
    if ld and isinstance(ld.get("offers"), (dict, list)):
        offers = ld["offers"][0] if isinstance(ld["offers"], list) else ld["offers"]
        price = _to_float_safe(offers.get("price"))
        currency = _first_str(offers.get("priceCurrency"))
    if price is None:
        # Fallback to common amount element
        frac = soup.select_one(".andes-money-amount__fraction")
        cents = soup.select_one(".andes-money-amount__cents")
        if frac:
            amount = frac.get_text(strip=True) + (("." + cents.get_text(strip=True)) if cents else "")
            price = _to_float_safe(amount)
        symbol_node = soup.select_one(".andes-money-amount__currency-symbol")
        if not currency and symbol_node:
            # Very rough mapping from common symbols
            symbol = symbol_node.get_text(strip=True)
            currency = {"$": "ARS", "R$": "BRL", "U$S": "USD"}.get(symbol, None)

    # Rating & Reviews
    rating = None
    reviews = None
    if ld and isinstance(ld.get("aggregateRating"), dict):
        ar = ld["aggregateRating"]
        rating = _to_float_safe(ar.get("ratingValue"))
        reviews = _to_int_safe(ar.get("reviewCount"))
    if rating is None:
        node = soup.select_one("[itemprop='ratingValue'], .ui-pdp-review__rating")
        if node:
            rating = _to_float_safe(node.get_text(strip=True))
    if reviews is None:
        node = soup.select_one("[itemprop='reviewCount'], .ui-pdp-review__amount")
        if node:
            reviews = _to_int_safe(node.get_text(strip=True))

    # Condition
    condition = None
    if ld and isinstance(ld.get("offers"), (dict, list)):
        offers = ld["offers"][0] if isinstance(ld["offers"], list) else ld["offers"]
        condition = _first_str(offers.get("itemCondition"))
        if condition:
            condition = condition.split("/")[-1]  # schema.org/UsedCondition -> UsedCondition
    if not condition:
        node = soup.find(string=re.compile(r"(Nuevo|Usado|Refurbished|Reacondicionado)", re.I))
        condition = node.strip() if isinstance(node, str) else None

    # Description
    description = None
    if ld:
        description = _first_str(ld.get("description"))
    if not description:
        node = soup.select_one(".ui-pdp-description__content, #tab-description, .item-description__text")
        if node:
            description = node.get_text("\n", strip=True)

    # Quantity available (best-effort)
    quantity_available = None
    qty_node = soup.find(string=re.compile(r"Disponibles?:\s*\d+", re.I))
    if isinstance(qty_node, str):
        m = re.search(r"(\d+)", qty_node)
        if m:
            quantity_available = int(m.group(1))
    if quantity_available is None and ld and isinstance(ld.get("offers"), (dict, list)):
        offers = ld["offers"][0] if isinstance(ld["offers"], list) else ld["offers"]
        quantity_available = _to_int_safe(offers.get("inventoryLevel", {}).get("value"))

    # Seller info
    seller_name, seller_rating = extract_seller_from_soup(soup, ld)

    # Images
    images = _images_from_soup(soup)

    product: Dict[str, Any] = {
        "title": title,
        "price": price,
        "currency": currency,
        "rating": rating,
        "reviews": reviews,
        "condition": condition,
        "seller": seller_name,
        "seller_rating": seller_rating,
        "quantity_available": quantity_available,
        "description": description,
        "images": images,
        "url": url,
    }

    # Clean up Nones for nicer output
    return {k: v for k, v in product.items() if v is not None}