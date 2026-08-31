#!/usr/bin/env python3
"""
Data Quality Gate for Learning → Strategy pipeline.

Ensures only LIVE or valid CACHED data can update production strategies.
SAMPLE / NOT_AVAILABLE / synthetic data is blocked from changing strategy.

Usage:
    from data_quality_gate import is_valid_for_strategy, mark_sample, DATA_SOURCE

    records = get_real_data()
    if not records:
        records = mark_sample(get_sample_fallback())
    # ... learn from records ...
    if is_valid_for_strategy(records):
        write_strategy(strategy)
    else:
        logger.warning("SAMPLE data detected, strategy update skipped")
"""
from typing import Any, Dict, List, Optional

# Data source constants
DATA_SOURCE_LIVE = "LIVE"
DATA_SOURCE_CACHED = "CACHED"
DATA_SOURCE_SAMPLE = "SAMPLE"
DATA_SOURCE_NOT_AVAILABLE = "NOT_AVAILABLE"
DATA_SOURCE_SYNTHETIC = "SYNTHETIC"

# Sources allowed to update production strategy
VALID_STRATEGY_SOURCES = {DATA_SOURCE_LIVE, DATA_SOURCE_CACHED}

# Sources that must NEVER update production strategy
BLOCKED_SOURCES = {DATA_SOURCE_SAMPLE, DATA_SOURCE_NOT_AVAILABLE, DATA_SOURCE_SYNTHETIC}


def get_data_source(record: Dict[str, Any]) -> str:
    """Extract data_source from a record; defaults to LIVE if not marked."""
    return str(record.get("data_source", DATA_SOURCE_LIVE)).upper()


def mark_sample(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Mark records as SAMPLE data (used when real data fetch fails)."""
    for r in records:
        r["data_source"] = DATA_SOURCE_SAMPLE
    return records


def mark_cached(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Mark records as valid CACHED data (from local snapshot/cache)."""
    for r in records:
        r["data_source"] = DATA_SOURCE_CACHED
    return records


def is_valid_for_strategy(records: List[Dict[str, Any]]) -> bool:
    """
    Check if records are valid for updating production strategy.
    Returns False if ANY record is SAMPLE/NOT_AVAILABLE/SYNTHETIC,
    or if the list is empty.
    """
    if not records:
        return False
    for r in records:
        src = get_data_source(r)
        if src in BLOCKED_SOURCES:
            return False
    return True


def strategy_update_allowed(records: List[Dict[str, Any]], logger=None) -> bool:
    """
    Gate function: returns True if strategy update is allowed, False otherwise.
    Logs a warning when blocked.
    """
    if is_valid_for_strategy(records):
        return True
    sources = set(get_data_source(r) for r in records) if records else {"EMPTY"}
    msg = f"策略更新被拦截: 数据来源={sources} (仅LIVE/CACHED可更新策略)"
    if logger:
        logger.warning(msg)
    else:
        print(f"  ⚠️ {msg}")
    return False
