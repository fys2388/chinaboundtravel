"""P0-7: affiliate click attribution tests.

The article affiliate section must expose the unified event model data
(content_id, partner, placement, channel) and emit an `affiliate_click` GA4
event without changing any affiliate URLs.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SINGLE = (REPO_ROOT / "layouts" / "_default" / "single.html").read_text(encoding="utf-8", errors="replace")
HUGO_TOML = (REPO_ROOT / "hugo.toml").read_text(encoding="utf-8")


def test_partner_attributes_present():
    for partner in ("esim", "vpn", "hotel", "klook"):
        assert f'data-affiliate-partner="{partner}"' in SINGLE
        assert 'data-affiliate-placement="article_cta"' in SINGLE


def test_content_id_and_channel_attributes():
    assert "data-content-id" in SINGLE
    assert 'data-channel="organic"' in SINGLE


def test_event_model_emitted():
    assert "affiliate_click" in SINGLE
    assert "gtag('event', 'affiliate_click', eventParams)" in SINGLE
    for field in ("content_id", "partner", "placement", "channel", "timestamp", "destination", "tracking_parameter"):
        assert field in SINGLE


def test_no_affiliate_url_changed():
    """hrefs must still be template-driven params (no hardcoded URL changes)."""
    for key in ("esim", "vpn", "hotel", "klook"):
        assert "{{{{ .Site.Params.affiliate.{key} }}}}".format(key=key) in SINGLE
    # hugo.toml affiliate params must still carry the verified tracking config
    for marker in ("aid=730795", "aff_id=150687", "klook.tpo.li", "safetywing.com/nomad-insurance?referenceID=26548976"):
        assert marker in HUGO_TOML