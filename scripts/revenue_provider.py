#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-GROWTH-14A: Revenue Provider Abstraction.

Single source of truth for revenue availability. Current status is
REVENUE_NOT_AVAILABLE: no affiliate revenue API is connected yet.

Design rules:
  - deterministic, no network calls
  - NEVER fabricate revenue, orders or commissions
  - future providers (Travelpayouts API, Booking, Klook, Airalo) plug in
    behind the same interface without changing consumers

Consumers:
  - scripts/revenue_measurement.py
  - scripts/revenue_experiment_review.py
  - scripts/affiliate_funnel_audit.py
  - tests/test_affiliate_funnel_measurement.py
"""
from __future__ import annotations

from datetime import date

REVENUE_STATUS = "REVENUE_NOT_AVAILABLE"
# Status values the abstraction understands today.
KNOWN_STATUSES = ("REVENUE_NOT_AVAILABLE", "PARTIAL", "AVAILABLE")


class RevenueProvider:
    """Provider interface. Subclasses map to real partner dashboards/APIs.

    Current implementation returns None revenue and reports
    REVENUE_NOT_AVAILABLE so that every pipeline downstream treats revenue
    as unknown instead of inventing numbers.
    """

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


def get_active_provider() -> RevenueProvider:
    """Return the active provider. Today always the unavailable stub."""
    return RevenueProvider("none")


if __name__ == "__main__":
    p = get_active_provider()
    print(f"provider={p.provider_name} status={p.status} revenue={p.get_revenue()!r}")
