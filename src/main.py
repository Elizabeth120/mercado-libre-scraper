import argparse
import json
import logging
import os
import sys
from typing import List, Dict, Any

# Allow running tests without installing as a package
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.http_client import HttpClient
from extractors.product_parser import parse_product
from utils.country_mapper import normalize_country_or_url

def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

def load_input(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run(urls: List[str], timeout: int = 20, proxy: str = None) -> List[Dict[str, Any]]:
    client = HttpClient(timeout=timeout, proxy=proxy)
    results: List[Dict[str, Any]] = []
    for raw in urls:
        url = normalize_country_or_url(raw)
        logging.info("Fetching %s", url)
        try:
            html = client.get(url)
            product = parse_product(html, url=url)
            results.append(product)
            logging.debug("Parsed product from %s => %s", url, product.get("title"))
        except Exception as e:
            logging.exception("Failed to process %s: %s", url, e)
    return results

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mercado Libre Scraper - fetch and parse product pages into JSON."
    )
    parser.add_argument(
        "--url",
        action="append",
        help="Product URL to scrape (repeatable). If omitted, --input is used.",
    )
    parser.add_argument(
        "--input",
        help="Path to JSON file with {'urls': ['...']} or {'country':'mx','paths':['/p/xxx']}.",
    )
    parser.add_argument(
        "--out",
        help="Path to write JSON results. If omitted, prints to stdout.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Request timeout in seconds (default: 20)",
    )
    parser.add_argument(
        "--proxy",
        type=str,
        default=os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy"),
        help="HTTP(S) proxy URL (default from HTTP_PROXY env if set).",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Increase verbosity (-v, -vv)"
    )
    args = parser.parse_args()
    configure_logging(args.verbose)

    urls: List[str] = []
    if args.url:
        urls.extend(args.url)

    if args.input and not urls:
        payload = load_input(args.input)
        if "urls" in payload:
            urls.extend(payload["urls"])
        elif "country" in payload and "paths" in payload:
            country = payload["country"]
            for p in payload["paths"]:
                urls.append(f"{country}:{p}")
        else:
            raise SystemExit(
                "Unsupported input JSON. Expect {'urls': [...]} or {'country': 'mx', 'paths': [...]}"
            )

    if not urls:
        # Fallback to included sample file for convenience
        sample = os.path.join(os.path.dirname(PROJECT_ROOT), "data", "input_samples.json")
        if os.path.exists(sample):
            logging.warning("No URLs provided. Using bundled sample: %s", sample)
            payload = load_input(sample)
            urls = payload.get("urls", [])
        else:
            raise SystemExit("No URLs provided. Use --url or --input.")

    results = run(urls, timeout=args.timeout, proxy=args.proxy)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(args.out)
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()