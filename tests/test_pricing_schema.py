"""V6-3: Pricing page structured data regression tests.

Ensures:
  - the pricing page emits Product + Offer JSON-LD (not BlogPosting)
  - schema prices match the visible prices on the pricing table
  - no fabricated aggregateRating / review / ratingValue
  - the JSON-LD block parses as valid JSON
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SCHEMA = (REPO_ROOT / "layouts" / "partials" / "templates" / "schema_json.html").read_text(encoding="utf-8")
PRICING = (REPO_ROOT / "layouts" / "partials" / "pricing-table.html").read_text(encoding="utf-8")


def extract_pricing_schema():
    marker = SCHEMA.find('"@type": "Product"')
    start = SCHEMA.rfind("{", 0, marker)
    assert start != -1, "Product schema block not found"
    tail = SCHEMA[start:]
    end = tail.find("}\n</script>")
    assert end != -1, "Product schema block has no closing tag"
    return json.loads(tail[: end + 1])


def test_schema_is_valid_json():
    data = extract_pricing_schema()
    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "Product"
    assert len(data["offers"]) >= 1


def test_schema_prices_match_visible_prices():
    data = extract_pricing_schema()
    visible = set(re.findall(r'class="amount">\$(\d+(?:\.\d+)?)</span>', PRICING))
    schema_prices = {str(offer["price"]) for offer in data["offers"]}
    assert visible == schema_prices, (visible, schema_prices)
    assert all(offer["priceCurrency"] == "USD" for offer in data["offers"])
    assert all(offer["availability"] == "https://schema.org/InStock" for offer in data["offers"])


def test_no_fake_rating_or_review():
    data = extract_pricing_schema()
    dumped = json.dumps(data)
    assert "aggregateRating" not in dumped
    assert "review" not in dumped
    assert "ratingValue" not in dumped


def test_pricing_page_not_blog_posting():
    # The pricing branch must render instead of the BlogPosting branch.
    pricing_branch = SCHEMA.split('{{- if .Type | eq "pricing" }}', 1)[1]
    pricing_branch = pricing_branch.split("{{- else }}", 1)[0]
    assert '"@type": "Product"' in pricing_branch
    assert "BlogPosting" not in pricing_branch

