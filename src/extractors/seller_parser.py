from typing import Any, Dict, Optional, Tuple

from bs4 import BeautifulSoup

def extract_seller_from_soup(
    soup: BeautifulSoup, ldjson: Dict[str, Any]
) -> Tuple[Optional[str], Optional[float]]:
    """
    Extract seller name and rating; prefer JSON-LD if present, fall back to UI selectors.
    """
    name: Optional[str] = None
    rating: Optional[float] = None

    if ldjson:
        seller = ldjson.get("brand") or ldjson.get("seller")
        if isinstance(seller, dict):
            name = seller.get("name") or name
        elif isinstance(seller, str):
            name = seller or name

    if not name:
        node = soup.select_one(".ui-pdp-seller__link-trigger, a[href*='seller'], .reputation__title")
        if node:
            name = node.get_text(strip=True)

    # Best-effort rating near seller box
    if rating is None:
        node = soup.select_one("[data-testid='seller_rating'], .reputation__title + .reputation__subtitle")
        if node:
            try:
                rating = float(node.get_text(strip=True).split()[0].replace(",", "."))
            except Exception:
                pass

    return name, rating