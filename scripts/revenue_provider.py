#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-GROWTH-14A: Revenue Provider Abstraction.

Single source of truth for revenue availability. Now wired to the real
Travelpayouts Affiliate Statistics API via scripts/travelpayouts_client.py:
when TRAVELPAYOUTS_API_TOKEN is present the active provider returns real
revenue/clicks; otherwise it degrades to REVENUE_NOT_AVAILABLE and returns
None.

Hard rules:
  - NEVER fabricate revenue, orders or commissions
  - API failure / no token -> None (unknown), never a made-up number
  - future providers (Booking, Klook, Airalo) plug in behind the same
    interface without changing consumers

Consumers:
  - scripts/revenue_measurement.py
  - scripts/revenue_experiment_review.py
  - scripts/affiliate_funnel_audit.py
  - tests/test_affiliate_funnel_measurement.py
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

import travelpayouts_client

REVENUE_STATUS = (
    "AVAILABLE" if os.environ.get("TRAVELPAYOUTS_API_TOKEN", "").strip()
    else "REVENUE_NOT_AVAILABLE"
)
# Status values the abstraction understands today.
KNOWN_STATUSES = ("REVENUE_NOT_AVAILABLE", "PARTIAL", "AVAILABLE")


class RevenueProvider:
    """Provider interface. Subclasses map to real partner dashboards/APIs."""

    def __init__(self, provider_name: str = "none") -> None:
        self.provider_name = provider_name
        self._status = REVENUE_STATUS

    @property
    def status(self) -> str:
        return self._status

    def get_revenue(self, days: int = 28):
        """Return revenue for the last `days` days, or None when unavailable."""
        if days <= 0:
            raise ValueError("days must be > 0")
        return None

    def get_affiliate_clicks(self, days: int = 28):
        """Return affiliate click count, or None when unavailable."""
        if days <= 0:
            raise ValueError("days must be > 0")
        return None

    def baseline_period(self, days: int = 28):
        """Return (start, end) ISO dates for a trailing window ending today."""
        if days <= 0:
            raise ValueError("days must be > 0")
        end = date.today()
        start = end.fromordinal(end.toordinal() - days + 1)
        return start.isoformat(), end.isoformat()


class TravelpayoutsProvider(RevenueProvider):
    """Real Travelpayouts revenue provider (P1-GROWTH-14A).

    Returns real API numbers when TRAVELPAYOUTS_API_TOKEN is configured and
    the call succeeds; returns None otherwise. Never fabricates.
    """

    def __init__(self) -> None:
        super().__init__("travelpayouts")
        self._status = REVENUE_STATUS

    def _enabled(self) -> bool:
        return bool(os.environ.get("TRAVELPAYOUTS_API_TOKEN", "").strip())

    def get_revenue(self, days: int = 28):
        if days <= 0:
            raise ValueError("days must be > 0")
        if not self._enabled():
            return None
        stats = travelpayouts_client.fetch_affiliate_stats(days=days)
        return stats["revenue"] if stats else None

    def get_affiliate_clicks(self, days: int = 28):
        if days <= 0:
            raise ValueError("days must be > 0")
        if not self._enabled():
            return None
        stats = travelpayouts_client.fetch_affiliate_stats(days=days)
        return stats["clicks"] if stats else None


def get_active_provider() -> RevenueProvider:
    """Return the active provider: Travelpayouts when token configured, else stub."""
    if os.environ.get("TRAVELPAYOUTS_API_TOKEN", "").strip():
        return TravelpayoutsProvider()
    return RevenueProvider("none")


if __name__ == "__main__":
    p = get_active_provider()
    print(f"provider={p.provider_name} status={p.status} "
          f"revenue={p.get_revenue()!r} clicks={p.get_affiliate_clicks()!r}")
