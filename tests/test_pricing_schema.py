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


# ---------------------------------------------------------------------------
# P0 fix: button href must match the plan shown on the card AND the schema Offer
# (regression: onetime/annual Stripe links were swapped in production)
# ---------------------------------------------------------------------------
ONETIME_URL = "https://buy.stripe.com/14A7sF1vWcEH3mxc1m1gs03"
MONTHLY_URL = "https://buy.stripe.com/fZudR35McdILaOZ9Te1gs05?prefilled_coupon=FIRSTMONTH1"
ANNUAL_URL = "https://buy.stripe.com/28E8wJ4I8bADg9je9u1gs01"


def test_button_links_match_plans():
    assert f'id="btn-onetime" href="{ONETIME_URL}"' in PRICING
    assert f'id="btn-monthly" href="{MONTHLY_URL}"' in PRICING
    assert f'id="btn-annual" href="{ANNUAL_URL}"' in PRICING


def test_js_links_match_plans():
    assert f"'btn-onetime': '{ONETIME_URL}'" in PRICING
    assert f"'btn-monthly': '{MONTHLY_URL}'" in PRICING
    assert f"'btn-annual': '{ANNUAL_URL}'" in PRICING


def test_schema_offer_urls_match_button_links():
    data = extract_pricing_schema()
    by_name = {o["name"]: o["url"] for o in data["offers"]}
    assert by_name["One-Time Buyout"] == ONETIME_URL
    assert by_name["Monthly Radar (first month)"] == MONTHLY_URL
    assert by_name["Annual Elite Pass"] == ANNUAL_URL


def test_no_swapped_stripe_links():
    # One-Time card must not point at the Annual checkout and vice versa
    onetime_href = PRICING.split('id="btn-onetime" href="', 1)[1].split('"', 1)[0]
    annual_href = PRICING.split('id="btn-annual" href="', 1)[1].split('"', 1)[0]
    assert onetime_href != annual_href
    assert onetime_href == ONETIME_URL
    assert annual_href == ANNUAL_URL
