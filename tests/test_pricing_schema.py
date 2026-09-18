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

import pytest

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
#
# P0 fix 2 (2026-09-18): FIRSTMONTH1 优惠码在 Stripe 后台从未创建，带
# ?prefilled_promo_code=FIRSTMONTH1 的 Payment Link 会静默跳过折扣、按原价
# $9.99 扣款。按钮原先宣称「Start for $1 / auto-applied」而实际扣 $9.99，
# 属误导性定价表述；schema 也报 price="1" 与实际不一致（搜索质量风险）。
# 修法是把三处（按钮 href / JS 链接表 / schema Offer）的 promo 码全去掉、
# 价格改回 $9.99。优惠码建好后加回来即可，Payment Link 本身无需改。
ONETIME_URL = "https://buy.stripe.com/14A7sF1vWcEH3mxc1m1gs03"
MONTHLY_URL = "https://buy.stripe.com/fZudR35McdILaOZ9Te1gs05"
ANNUAL_URL = "https://buy.stripe.com/28E8wJ4I8bADg9je9u1gs01"
PROMO_CODE = "FIRSTMONTH1"


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
    assert by_name["Monthly Radar"] == MONTHLY_URL
    assert by_name["Annual Elite Pass"] == ANNUAL_URL


def test_no_swapped_stripe_links():
    # One-Time card must not point at the Annual checkout and vice versa
    onetime_href = PRICING.split('id="btn-onetime" href="', 1)[1].split('"', 1)[0]
    annual_href = PRICING.split('id="btn-annual" href="', 1)[1].split('"', 1)[0]
    assert onetime_href != annual_href
    assert onetime_href == ONETIME_URL
    assert annual_href == ANNUAL_URL


# ---------------------------------------------------------------------------
# P0 fix 2: 不存在的优惠码不得出现在任何对外可见的位置
# ---------------------------------------------------------------------------

def _strip_html_comments(text: str) -> str:
    """去掉 HTML 注释。

    注释里可以保留 promo 码字样作为「为什么移除了它」的说明，
    那不对用户可见，不该算作对外宣称。
    """
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def test_promo_code_absent_from_pricing_layout():
    """FIRSTMONTH1 从未在 Stripe 创建，带它的链接会按原价扣款。

    按钮写 $1、实际扣 $9.99 是误导性定价表述。优惠码建好之前，
    promo 码不得出现在任何**对用户可见**的位置（href / JS 链接表 / 文案）。
    """
    visible = _strip_html_comments(PRICING)
    assert PROMO_CODE not in visible


def test_promo_code_absent_from_schema():
    data = extract_pricing_schema()
    assert PROMO_CODE not in json.dumps(data)
    for offer in data["offers"]:
        assert PROMO_CODE not in offer.get("url", "")


def test_no_false_first_month_claim():
    """不得宣称「首月 $1」——那是对不存在优惠码的承诺。

    注意 $1 要用独立 token 匹配：$14.99（一次性买断价）里含 $1 的字面量，
    但那不是首月促销。
    """
    visible = _strip_html_comments(PRICING)
    assert "first month" not in visible.lower()
    assert not re.search(r"\$1(?![\d.])", visible)
    assert not re.search(r">\$1<", visible)


def test_monthly_offer_price_is_the_real_price():
    """schema 报价必须是用户实际会被扣的金额。"""
    data = extract_pricing_schema()
    monthly = [o for o in data["offers"] if o["name"] == "Monthly Radar"]
    assert len(monthly) == 1
    assert monthly[0]["price"] == "9.99"


def test_monthly_visible_price_matches_schema():
    """卡片上显示的月付价格必须与 schema 一致，且不含已作废的 $1 首月价。"""
    data = extract_pricing_schema()
    schema_prices = {str(o["price"]) for o in data["offers"]}
    visible = set(re.findall(r'class="amount">\$(\d+(?:\.\d+)?)</span>', PRICING))
    assert "9.99" in visible
    assert "1" not in visible
    assert visible == schema_prices


# ---------------------------------------------------------------------------
# P0 fix 2 覆盖面：不止定价表，所有对外宣称月付价格的 partial 都要干净
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "partial",
    [
        "layouts/partials/pricing-table.html",
        "layouts/partials/ebook-promo.html",
        "layouts/partials/sidebar-author.html",
        "layouts/partials/templates/schema_json.html",
    ],
)
def test_no_false_monthly_pricing_claim_in_partial(partial):
    """首月 $1 的说法曾同时出现在 4 个 partial 里。

    只改定价表会留下侧栏 / ebook 卡片继续对不存在优惠码做承诺。
    """
    p = REPO_ROOT / partial
    assert p.exists(), f"缺少 {partial}"
    text = _strip_html_comments(p.read_text(encoding="utf-8", errors="replace"))
    assert PROMO_CODE not in text, f"{partial} 仍含 promo 码"
    assert "first month" not in text.lower(), f"{partial} 仍宣称首月价"
    assert not re.search(r"\$1(?![\d.])", text), f"{partial} 仍含 $1 独立价格"

