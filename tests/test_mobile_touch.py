"""V6-3: Mobile touch target regression tests.

Ensures interactive controls reach roughly 44x44 CSS px without enlarging
the visible icon:
  - header theme toggle and hamburger (mobile menu) button
  - mobile menu links
  - primary CTA (subscribe) is at least 44px tall
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

NAV_CSS = (REPO_ROOT / "assets" / "css" / "extended" / "custom-nav.css").read_text(encoding="utf-8")
CUSTOM_CSS = (REPO_ROOT / "assets" / "css" / "extended" / "custom.css").read_text(encoding="utf-8")


def test_header_toggle_buttons_have_44px_touch_area():
    block = NAV_CSS.split("#theme-toggle,", 1)[1].split("}", 1)[0]
    assert "min-width: 44px" in block
    assert "min-height: 44px" in block
    assert ".hamburger-btn" in NAV_CSS


def test_mobile_menu_links_have_44px_target():
    blocks = re.split(r"@media[^{]*\{", NAV_CSS)
    target = None
    for b in blocks:
        if ".menu a" in b and "min-height: 44px" in b:
            target = b
            break
    assert target is not None, "no .menu a rule with min-height: 44px"


def test_primary_cta_is_tall_enough():
    btn = CUSTOM_CSS.split(".subscribe-btn {", 1)[1].split("}", 1)[0]
    m = re.search(r"padding:\s*([\d.]+rem|[.\d]+px)\s+", btn)
    assert m, "subscribe button padding not found"
    top = m.group(1)
    px = float(top.replace("rem", "")) * 16 if "rem" in top else float(top)
    # 44px target: icon/text line box (~20px) + top/bottom padding
    assert px * 2 + 20 >= 44, (top, px)

