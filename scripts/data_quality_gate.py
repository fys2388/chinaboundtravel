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


# ============================================================================
# P1-AI-OPS-04: Extended Data Quality Gate (freshness + unified check)
# ============================================================================

DATA_SOURCE_LOCAL = "LOCAL"
DEFAULT_CACHE_MAX_HOURS = 24
DEFAULT_LOCAL_MAX_HOURS = 72


def mark_local(records):
    """Mark records as LOCAL data (from local file scan, not external API)."""
    from datetime import datetime
    for r in records:
        r["data_source"] = DATA_SOURCE_LOCAL
        if "data_timestamp" not in r:
            r["data_timestamp"] = datetime.now().isoformat()
    return records


def is_cache_fresh(record, max_hours=DEFAULT_CACHE_MAX_HOURS):
    """Check if a CACHED/LOCAL record is fresh enough (within max_hours)."""
    from datetime import datetime, timedelta
    ts_str = record.get("data_timestamp") or record.get("timestamp") or record.get("fetched_at")
    if not ts_str:
        return False
    try:
        ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        if ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)
        return (datetime.now() - ts) <= timedelta(hours=max_hours)
    except (ValueError, TypeError):
        return False


def check_data_quality(records, domain="unknown", cache_max_hours=DEFAULT_CACHE_MAX_HOURS, local_max_hours=DEFAULT_LOCAL_MAX_HOURS):
    """Unified data quality check for learning loops. Returns detailed report."""
    from datetime import datetime
    result = {
        "domain": domain,
        "checked_at": datetime.now().isoformat(),
        "total_records": len(records) if records else 0,
        "passed": False,
        "blocked": True,
        "sources": {},
        "stale_count": 0,
        "reasons": [],
        "summary": "",
    }
    if not records:
        result["reasons"].append("EMPTY: no data records")
        result["summary"] = "BLOCKED: empty data"
        return result
    for r in records:
        src = get_data_source(r)
        result["sources"][src] = result["sources"].get(src, 0) + 1
    blocked_sources = set(result["sources"].keys()) & BLOCKED_SOURCES
    if blocked_sources:
        result["reasons"].append("BLOCKED_SOURCE: detected " + str(blocked_sources))
    stale = 0
    for r in records:
        src = get_data_source(r)
        if src == DATA_SOURCE_CACHED and not is_cache_fresh(r, cache_max_hours):
            stale += 1
        elif src == DATA_SOURCE_LOCAL and not is_cache_fresh(r, local_max_hours):
            stale += 1
    result["stale_count"] = stale
    if stale > 0:
        result["reasons"].append("STALE_CACHE: " + str(stale) + " records exceed freshness threshold")
    if not blocked_sources and stale == 0:
        result["passed"] = True
        result["blocked"] = False
        result["summary"] = "PASSED: " + str(result["sources"]) + " (" + str(len(records)) + " records)"
    else:
        result["summary"] = "BLOCKED: " + "; ".join(result["reasons"])
    return result


def should_block_strategy_update(records, domain="unknown", cache_max_hours=DEFAULT_CACHE_MAX_HOURS, print_report=True):
    """Convenience: returns True if strategy update SHOULD BE BLOCKED."""
    report = check_data_quality(records, domain, cache_max_hours)
    if print_report:
        print("  [DQG][" + domain + "] " + report["summary"])
        for reason in report["reasons"]:
            print("    - " + reason)
    return report["blocked"]
