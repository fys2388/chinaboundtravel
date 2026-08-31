#!/usr/bin/env python3
"""
Strategy Change Logger — standardized audit records for strategy updates.

Ensures every strategy change has: version, timestamp, field, old, new,
reason, evidence. Provides rollback reference via previous_version tracking.

Usage:
    from strategy_change_logger import make_change, get_version
    strategy_changes.append(make_change(
        field="instagram.best_hooks",
        old=["old"], new=["new"],
        reason="基于Top 20%高CTR帖子分析",
        evidence="CTR提升15%, n=42帖子"
    ))
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

STRATEGY_VERSION = "2.1"


def get_version() -> str:
    """Return current strategy version."""
    return STRATEGY_VERSION


def make_change(
    field: str,
    old: Any,
    new: Any,
    reason: str,
    evidence: Optional[str] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a standardized strategy change record with full audit metadata.

    Args:
        field: Dot-path of the changed field (e.g. "instagram.best_hooks")
        old: Previous value
        new: New value
        reason: Human-readable reason for the change
        evidence: Data evidence supporting the change (optional)
        version: Strategy version (defaults to STRATEGY_VERSION)

    Returns:
        Dict with all audit fields
    """
    return {
        "version": version or STRATEGY_VERSION,
        "timestamp": datetime.now().isoformat(),
        "field": field,
        "old": old,
        "new": new,
        "reason": reason,
        "evidence": evidence or "based on performance data analysis",
    }


def append_change(
    changes_list: List[Dict[str, Any]],
    field: str,
    old: Any,
    new: Any,
    reason: str,
    evidence: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Append a standardized change record to a list and return it."""
    changes_list.append(make_change(field, old, new, reason, evidence))
    return changes_list


def build_rollback_ref(strategy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a rollback reference snapshot from the current strategy.
    Call BEFORE applying changes to preserve the pre-change state.
    """
    return {
        "version": strategy.get("version", "unknown"),
        "last_updated": strategy.get("last_updated", "unknown"),
        "snapshot": {
            k: v for k, v in strategy.items()
            if k not in ("strategy_changes", "rollback_reference")
        },
    }
