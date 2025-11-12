import json
import os
import sys

# Ensure src is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from extractors.product_parser import parse_product  # noqa: E402

def sample_html() -> str:
    ld = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "Cámara Fotográfica XYZ 24MP",
        "image": [
            "https://http2.mlstatic.com/img1.webp",
            "https://http2.mlstatic.com/img2.webp"
        ],
        "description": "Cámara compacta con zoom óptico 10x",
        "brand": {"@type": "Brand", "name": "FotoMax"},
        "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.6", "reviewCount": "132"},
        "offers": {
            "@type": "Offer",
            "priceCurrency": "MXN",
            "price": "3599.90",
            "itemCondition": "https://schema.org/NewCondition"
        }
    }
    return f"""
    <html><head>
      <script type="application/ld+json">{json.dumps(ld)}</script>
    </head>
    <body>
      <h1 class="ui-pdp-title">Cámara Fotográfica XYZ 24MP</h1>
      <div class="andes-money-amount__fraction">3.599</div><div class="andes-money-amount__cents">90</div>
    </body></html>
    """

def test_parse_product_from_ldjson():
    html = sample_html()
    data = parse_product(html, url="https://www.mercadolibre.com.mx/p/XYZ")
    assert data["title"] == "Cámara Fotográfica XYZ 24MP"
    assert abs(float(data["price"]) - 3599.90) < 1e-6
    assert data["currency"] == "MXN"
    assert data["rating"] == 4.6
    assert data["reviews"] == 132
    assert data["condition"] == "NewCondition" or data["condition"] == "New"
    assert data["seller"] == "FotoMax"
    assert len(data["images"]) >= 2
    assert data["url"].endswith("/XYZ")