"""P0-5: high-risk content human gate tests.

HIGH-risk content must NOT auto-publish; LOW/MEDIUM content must keep flowing
through the existing automation.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_risk_gate as gate

REPO_ROOT = Path(__file__).resolve().parent.parent

HIGH_FRONT = """---
title: "High Risk Visa Guide"
draft: false
risk_level: "high"
audit_status: "pending"
---
Content about visa rules.
"""

LOW_FRONT = """---
title: "Low Risk Food Guide"
draft: false
risk_level: "low"
audit_status: "pending"
---
Content about street food.
"""

MEDIUM_FRONT = """---
title: "Medium Risk Hotel Guide"
draft: false
risk_level: "medium"
audit_status: "pending"
---
Content about hotels.
"""


def test_high_risk_blocks(tmp_path):
    f = tmp_path / "visa.md"
    f.write_text(HIGH_FRONT, encoding="utf-8")
    blocked, risk = gate.gate_file(f, rewrite=False)
    assert blocked is True
    assert risk == "high"


def test_high_risk_rewritten_to_draft(tmp_path):
    f = tmp_path / "visa.md"
    f.write_text(HIGH_FRONT, encoding="utf-8")
    blocked, risk = gate.gate_file(f, rewrite=True)
    assert blocked is True
    text = f.read_text(encoding="utf-8")
    assert "draft: true" in text
    assert 'audit_status: "pending_review"' in text


def test_low_risk_passes(tmp_path):
    f = tmp_path / "food.md"
    f.write_text(LOW_FRONT, encoding="utf-8")
    blocked, risk = gate.gate_file(f, rewrite=False)
    assert blocked is False
    assert risk == "low"


def test_medium_risk_passes(tmp_path):
    f = tmp_path / "hotel.md"
    f.write_text(MEDIUM_FRONT, encoding="utf-8")
    blocked, risk = gate.gate_file(f, rewrite=False)
    assert blocked is False
    assert risk == "medium"


def test_high_risk_draft_is_not_blocked(tmp_path):
    f = tmp_path / "visa-draft.md"
    f.write_text(HIGH_FRONT.replace("draft: false", "draft: true"), encoding="utf-8")
    blocked, risk = gate.gate_file(f, rewrite=False)
    assert blocked is False
    assert risk == "high"


def test_cli_exit_codes(tmp_path):
    f = tmp_path / "visa.md"
    f.write_text(HIGH_FRONT, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_risk_gate.py"), "--files", str(f), "--no-rewrite"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1

    f2 = tmp_path / "food.md"
    f2.write_text(LOW_FRONT, encoding="utf-8")
    result2 = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_risk_gate.py"), "--files", str(f2), "--no-rewrite"],
        capture_output=True, text=True, timeout=30,
    )
    assert result2.returncode == 0