"""P0-1: Joran editorial persona governance tests.

Verifies that obviously fabricated first-person personal experiences are
flagged by the rule-based PersonaGuard (used by the ChiefEditor gate).
"""
import json
from pathlib import Path

import pytest

from persona_guard import PersonaGuard, load_governance_config

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def guard():
    return PersonaGuard()


@pytest.fixture(scope="module")
def config():
    return load_governance_config()


FABRICATED_SNIPPETS = [
    "I stayed at the Grand Hyatt Shanghai last month and loved the view.",
    "I visited the Great Wall in 2019, it was incredible.",
    "My wife and I tried the hotpot in Chengdu.",
    "When I traveled to Beijing, I booked a hotel near the Forbidden City.",
    "I personally experienced the rush hour metro in Shanghai.",
    "I booked my flight through the app and it was easy.",
    "I tried the xiaolongbao at that famous place.",
    "A local friend told me to avoid the tourist traps.",
    "I've lived in China for five years now.",
]

SAFE_SNIPPETS = [
    "In this guide, I will walk you through the visa application steps.",
    "If you are planning a trip to China, this guide covers what you need.",
    "ChinaBound Travel editors verify visa rules against official sources.",
    "Here is what our editorial team recommends for first-time visitors.",
    "This article was updated in August 2026.",
    "Travelers should check the official immigration website before departure.",
]


def test_governance_config_exists_and_valid():
    cfg_path = REPO_ROOT / "config" / "content_governance.json"
    assert cfg_path.exists()
    data = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    assert data["persona"]["rules"], "persona rules must not be empty"
    assert data["persona"]["forbidden_phrases"], "forbidden phrases must not be empty"
    assert {"low", "medium", "high"} <= set(data["risk_levels"].keys())


@pytest.mark.parametrize("snippet", FABRICATED_SNIPPETS)
def test_fabricated_experiences_are_blocked(guard, snippet):
    violations = guard.check(snippet)
    assert violations, f"expected fabrication to be flagged: {snippet!r}"


@pytest.mark.parametrize("snippet", SAFE_SNIPPETS)
def test_editorial_voice_is_allowed(guard, snippet):
    assert guard.is_clean(snippet), f"editorial voice should pass: {snippet!r}"


def test_persona_prompt_no_longer_requests_fabrication():
    """The generator prompt must not instruct the AI to invent personal stories."""
    gen = (REPO_ROOT / "chinaboundtravel_social_bot" / "joran_blog_generator.py").read_text(encoding="utf-8")
    banned_instructions = [
        "Include AT LEAST 2 personal stories/first-person experiences",
        "Include MULTIPLE SPECIFIC stories from my 5 years in China",
        "Write from FIRST-PERSON perspective (as an American expat in Chengdu)",
        "Include PERSONAL experiences (e.g., \"I remember my first trip...\")",
    ]
    for instr in banned_instructions:
        assert instr not in gen, f"fabrication instruction still present: {instr!r}"
    # The persona must be defined as an editorial persona.
    assert "Editorial Persona" in gen or "EDITORIAL PERSONA" in gen


def test_governance_rules_injected_into_prompt():
    gen = (REPO_ROOT / "chinaboundtravel_social_bot" / "joran_blog_generator.py").read_text(encoding="utf-8")
    assert "JORAN EDITORIAL PERSONA RULES (MANDATORY)" in gen