#!/usr/bin/env python3
"""
Generic Strategy Consumer — load and apply learning strategies to intelligent agents.

Provides a minimal, safe interface for agents to consume their respective
optimization strategy JSON files produced by the Learning Closed Loops.

Usage:
    from strategy_consumer import StrategyConsumer
    consumer = StrategyConsumer("reports/seo/seo_optimization_strategy.json")
    if consumer.available:
        priorities = consumer.get_priority_list("high_priority_keywords")
        sorted_items = consumer.sort_by_priority(items, priorities, "keyword")
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("strategy_consumer")


class StrategyConsumer:
    """Load a strategy JSON and apply its priorities to agent output."""

    def __init__(self, strategy_path: str, agent_name: str = "agent"):
        self.strategy_path = Path(strategy_path)
        self.agent_name = agent_name
        self.strategy: Dict[str, Any] = {}
        self.available: bool = False
        self.version: str = "unknown"
        self.last_updated: str = "unknown"
        self._load()

    def _load(self):
        """Load strategy file; fail silently if missing or invalid."""
        try:
            if not self.strategy_path.exists():
                logger.debug("[%s] Strategy file not found: %s", self.agent_name, self.strategy_path)
                return
            with open(self.strategy_path, encoding="utf-8") as f:
                self.strategy = json.load(f)
            self.version = str(self.strategy.get("version", "unknown"))
            self.last_updated = str(self.strategy.get("last_updated", "unknown"))
            self.available = True
            logger.info(
                "[%s] Strategy loaded: version=%s, updated=%s",
                self.agent_name, self.version, self.last_updated,
            )
        except Exception as e:
            logger.warning("[%s] Strategy load failed: %s", self.agent_name, e)
            self.available = False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a top-level strategy field."""
        if not self.available:
            return default
        return self.strategy.get(key, default)

    def get_priority_list(self, key: str) -> List[str]:
        """
        Get a priority list from strategy (e.g. high_priority_keywords, best_products).
        Handles both list-of-strings and list-of-dicts (extracts 'keyword'/'name'/'product').
        """
        if not self.available:
            return []
        raw = self.strategy.get(key, [])
        if not isinstance(raw, list):
            return []
        result = []
        for item in raw:
            if isinstance(item, str):
                result.append(item.lower().strip())
            elif isinstance(item, dict):
                for k in ("keyword", "name", "product", "term", "phrase"):
                    if k in item:
                        result.append(str(item[k]).lower().strip())
                        break
        return result

    def sort_by_priority(
        self,
        items: List[Dict[str, Any]],
        priority_key: str,
        item_field: str,
        default_priority: int = 999,
    ) -> List[Dict[str, Any]]:
        """
        Sort a list of item dicts by strategy priority.
        Items matching the strategy priority list get lower sort numbers (higher priority).

        Args:
            items: List of dicts to sort
            priority_key: Strategy key containing the priority list (e.g. "high_priority_keywords")
            item_field: Field in each item dict to compare against priority list
            default_priority: Priority value for items not in the strategy list

        Returns:
            Sorted list (strategy-prioritized first)
        """
        if not self.available or not items:
            return items
        priorities = self.get_priority_list(priority_key)
        if not priorities:
            return items

        def _priority_score(item: Dict) -> int:
            val = str(item.get(item_field, "")).lower().strip()
            for i, p in enumerate(priorities):
                if p in val or val in p:
                    return i
            return default_priority

        sorted_items = sorted(items, key=_priority_score)
        logger.info(
            "[%s] Applied strategy priority '%s': %d items sorted, %d matched",
            self.agent_name, priority_key, len(items),
            sum(1 for it in sorted_items if _priority_score(it) < default_priority),
        )
        return sorted_items

    def get_strategy_metadata(self) -> Dict[str, str]:
        """Return strategy metadata for logging/reporting."""
        return {
            "available": str(self.available),
            "version": self.version,
            "last_updated": self.last_updated,
            "strategy_file": str(self.strategy_path),
        }
