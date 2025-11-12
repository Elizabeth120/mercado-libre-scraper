import json
import os
import sys
from types import SimpleNamespace

# Ensure src is importable
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from main import run  # noqa: E402

def test_run_with_mocked_http(monkeypatch, tmp_path):
    # Minimal LD+JSON page
    payload = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "Teclado Mecánico ABC",
        "image": "https://http2.mlstatic.com/abc.webp",
        "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.2", "reviewCount": "17"},
        "offers": {"@type": "Offer", "priceCurrency": "BRL", "price": "199.00"}
    }
    html = f'<script type="application/ld+json">{json.dumps(payload)}</script>'

    class DummyClient:
        def __init__(self, *a, **kw):
            pass

        def get(self, url: str) -> str:
            # Return our static page for any URL
            return html

    # Patch HttpClient constructor used in main.run
    import main as main_mod
    monkeypatch.setattr(main_mod, "HttpClient", lambda timeout=None, proxy=None: DummyClient())

    urls = ["br:/produto/MLB999"]
    results = run(urls)
    assert isinstance(results, list)
    assert len(results) == 1
    item = results[0]
    assert item["title"] == "Teclado Mecánico ABC"
    assert item["price"] == 199.0
    assert item["currency"] == "BRL"
    assert item["rating"] == 4.2
    assert item["reviews"] == 17
    assert item["images"][0].endswith("abc.webp")