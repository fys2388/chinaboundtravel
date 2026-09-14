"""Shared SEO limits for content generation, validation and repair.

The Hugo head template renders ``title + " | ChinaBound Travel"`` while the
combined value is at most 60 characters. When the suffix would exceed that
limit, the template intentionally falls back to the page title alone. A front
matter title longer than 60 characters is therefore hard-truncated in HTML and
must be treated as invalid.
"""
from __future__ import annotations


TITLE_SUFFIX = " | ChinaBound Travel"
TITLE_RENDERED_MAX = 60
TITLE_HARD_MAX = 60
TITLE_MIN = 20


def is_title_too_long(title: str) -> bool:
    return len(title or "") > TITLE_HARD_MAX


def truncate_title(title: str, max_len: int = TITLE_HARD_MAX) -> str:
    """Trim a title without leaving a partial final word where practical."""
    value = (title or "").strip()
    if len(value) <= max_len:
        return value
    truncated = value[:max_len].rstrip()
    last_space = truncated.rfind(" ")
    if last_space >= max_len - 15:
        truncated = truncated[:last_space]
    return truncated.rstrip(" :,;-")
