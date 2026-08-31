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


def save_rollback(
    strategy: Dict[str, Any],
    strategy_file: str,
    domain: str,
    changes: Optional[List[Dict[str, Any]]] = None,
    log_file: str = None,
) -> Optional[Dict[str, Any]]:
    """
    Save a rollback snapshot to the append-only rollback log BEFORE strategy update.
    """
    import json
    import os
    from pathlib import Path

    try:
        if log_file is None:
            project_root = Path(__file__).parent.parent
            log_dir = project_root / "reports" / "orchestration"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = str(log_dir / "strategy_rollback_log.json")

        rollback_ref = build_rollback_ref(strategy)
        entry = {
            "rollback_id": datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + domain,
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "strategy_file": strategy_file,
            "pre_change_version": rollback_ref["version"],
            "pre_change_last_updated": rollback_ref["last_updated"],
            "snapshot": rollback_ref["snapshot"],
            "changes_applied": changes or [],
            "changes_count": len(changes) if changes else 0,
        }

        log_entries = []
        if os.path.exists(log_file):
            try:
                with open(log_file, encoding="utf-8") as f:
                    log_data = json.load(f)
                    if isinstance(log_data, list):
                        log_entries = log_data
                    elif isinstance(log_data, dict) and "entries" in log_data:
                        log_entries = log_data["entries"]
            except Exception:
                log_entries = []

        log_entries.append(entry)
        if len(log_entries) > 100:
            log_entries = log_entries[-100:]

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump({
                "log_version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "total_entries": len(log_entries),
                "entries": log_entries,
            }, f, ensure_ascii=False, indent=2)

        print(f"  \U0001f4e6 Rollback saved: {domain} (id={entry['rollback_id']}, changes={entry['changes_count']})")
        return entry

    except Exception as e:
        print(f"  \u26a0\ufe0f Rollback save failed ({domain}): {e}")
        return None
