#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Persona Guard - rule-based content guard for the Joran Editorial Persona.

Loads governance rules from config/content_governance.json and flags
AI-generated text that fabricates first-person personal travel experiences
(e.g., "I stayed at...", "My wife and I...", invented local quotes).

Used by:
  - chinaboundtravel_social_bot/joran_blog_generator.py (ChiefEditor gate)
  - tests/test_persona_governance.py
  - manual/CI content checks

No network access and no third-party dependencies.
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "content_governance.json"

DEFAULT_CONFIG = {
    "persona": {
        "forbidden_phrases": [
            "I stayed at",
            "I visited",
            "My wife and I",
            "When I traveled to",
            "I personally experienced",
            "I booked",
            "I tried",
        ],
        "rules": ["Joran is an editorial persona. Never fabricate personal travel experiences."],
    }
}


def load_governance_config(config_path=CONFIG_PATH):
    """Load the governance config; falls back to DEFAULT_CONFIG if missing."""
    try:
        with open(config_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return data
    except (OSError, json.JSONDecodeError):
        return DEFAULT_CONFIG


def forbidden_phrases(config=None):
    config = config or load_governance_config()
    return config.get("persona", {}).get("forbidden_phrases", [])


def _phrase_regex(phrase):
    """Build a case-insensitive regex for a phrase with flexible whitespace."""
    escaped = re.escape(phrase)
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(escaped, re.IGNORECASE)


class PersonaGuard:
    """Rule-based guard that detects fabricated first-person experiences."""

    def __init__(self, config=None):
        self.config = config or load_governance_config()
        self.patterns = [_phrase_regex(p) for p in forbidden_phrases(self.config)]
        self.rules = self.config.get("persona", {}).get("rules", [])

    def check(self, content):
        """Return a list of violation messages. Empty list means the content passes."""
        violations = []
        if not content:
            return violations
        for pattern in self.patterns:
            match = pattern.search(content)
            if match:
                start = max(0, match.start() - 40)
                end = min(len(content), match.end() + 40)
                snippet = content[start:end].replace("\n", " ")
                violations.append(
                    "[P0] Fabricated first-person experience pattern detected: "
                    f"'{match.group(0)}' ... context: ...{snippet}..."
                )
        return violations

    def is_clean(self, content):
        return not self.check(content)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/persona_guard.py <markdown_file_or_'-'>", file=sys.stderr)
        return 2

    arg = sys.argv[1]
    if arg == "-":
        content = sys.stdin.read()
    else:
        with open(arg, "r", encoding="utf-8") as f:
            content = f.read()

    guard = PersonaGuard()
    violations = guard.check(content)
    if violations:
        print("PERSONA_GUARD: FAIL")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("PERSONA_GUARD: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
