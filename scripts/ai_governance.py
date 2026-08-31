#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Governance Check - Kill Switch + L0-L3 Permission Boundaries

Single source of truth for AI safety. Loaded by all AI agents and workflows.

Usage:
    from ai_governance import check_kill_switch, check_permission, GovernanceError

    # Kill Switch check (call at start of every AI workflow)
    if not check_kill_switch():
        sys.exit(1)

    # Permission check (call before any write/publish action)
    if not check_permission("social", "optimize_social_hook"):
        raise GovernanceError("Agent 'social' not permitted to action 'optimize_social_hook'")
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

BLOG_ROOT = Path(__file__).resolve().parent.parent
GOVERNANCE_FILE = BLOG_ROOT / "config" / "ai_governance.json"


def load_governance() -> dict:
    """Load governance config. Returns empty dict if file missing (fail-open for read-only ops)."""
    try:
        with open(GOVERNANCE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def check_kill_switch(subsystem: Optional[str] = None) -> tuple[bool, str]:
    """Check if kill switch is active. Returns (is_safe: bool, reason: str).

    If global kill switch is enabled, ALL operations are blocked.
    If subsystem-specific kill switch is enabled, only that subsystem is blocked.
    """
    gov = load_governance()
    ks = gov.get("kill_switch", {})

    # Global kill switch
    if ks.get("global_enabled"):
        reason = ks.get("reason", "Global kill switch enabled")
        triggered = ks.get("triggered_at", "")
        return False, f"KILL_SWITCH_ACTIVE: {reason} (triggered: {triggered})"

    # Subsystem-specific kill switch
    if subsystem:
        subsystems = ks.get("subsystems", {})
        sub = subsystems.get(subsystem, {})
        if sub.get("enabled"):
            reason = sub.get("reason", f"{subsystem} kill switch enabled")
            return False, f"KILL_SWITCH_ACTIVE[{subsystem}]: {reason}"

    return True, "OK"


def check_permission(agent_name: str, action: str) -> tuple[bool, str]:
    """Check if an agent is permitted to perform an action. Returns (is_permitted: bool, reason: str).

    Permission levels:
        L0: Read Only - only read/analyze/report/audit/validate
        L1: Safe Automation - L0 + format/persona/dedup/schedule/report/metadata
        L2: Controlled Optimization - L1 + social hook/publish time/SEO title/CTA copy (with sample + rules + rollback)
        L3: High Risk - only flag for review, never auto-execute
    """
    gov = load_governance()
    agents = gov.get("agent_permissions", {})
    levels = gov.get("permission_levels", {})

    agent = agents.get(agent_name)
    if not agent:
        return False, f"AGENT_NOT_REGISTERED: '{agent_name}' not found in governance config"

    agent_level = agent.get("permission_level", "L0")

    # Check agent-specific deny list first
    denied = agent.get("denied", [])
    if action in denied:
        return False, f"PERMISSION_DENIED: action '{action}' is explicitly denied for agent '{agent_name}' (level {agent_level})"

    # Check agent-specific allow list
    allowed = agent.get("allowed", [])
    if action in allowed:
        return True, f"PERMISSION_GRANTED: action '{action}' allowed for agent '{agent_name}' (level {agent_level})"

    # Check level-based permissions
    level_config = levels.get(agent_level, {})
    level_allowed = level_config.get("allowed_actions", [])
    level_denied = level_config.get("denied_actions", [])

    if action in level_denied:
        return False, f"PERMISSION_DENIED: action '{action}' is denied at level {agent_level}"

    if action in level_allowed:
        return True, f"PERMISSION_GRANTED: action '{action}' allowed at level {agent_level}"

    # Action not found in any list - default deny for write actions, allow for read
    read_actions = {"read", "analyze", "report", "audit", "validate"}
    if action in read_actions:
        return True, f"PERMISSION_GRANTED: read-only action '{action}' allowed at all levels"

    return False, f"PERMISSION_UNKNOWN: action '{action}' not registered for agent '{agent_name}' (level {agent_level}). Add to governance config."


def require_permission(agent_name: str, action: str) -> None:
    """Raise GovernanceError if permission denied. Use in agents before write operations."""
    is_ok, reason = check_permission(agent_name, action)
    if not is_ok:
        raise GovernanceError(reason)


def require_kill_switch_safe(subsystem: Optional[str] = None) -> None:
    """Raise GovernanceError if kill switch is active. Call at start of every AI workflow."""
    is_safe, reason = check_kill_switch(subsystem)
    if not is_safe:
        raise GovernanceError(reason)


def get_agent_permission_level(agent_name: str) -> str:
    """Return the permission level of an agent."""
    gov = load_governance()
    return gov.get("agent_permissions", {}).get(agent_name, {}).get("permission_level", "L0")


def list_agents() -> list[dict]:
    """List all registered agents with their permission levels."""
    gov = load_governance()
    result = []
    for name, config in gov.get("agent_permissions", {}).items():
        result.append({
            "name": name,
            "label": config.get("name", name),
            "permission_level": config.get("permission_level", "L0"),
            "notes": config.get("notes", "")
        })
    return result


class GovernanceError(Exception):
    """Raised when a governance check fails (kill switch active or permission denied)."""
    pass


def main():
    """CLI: print governance status."""
    import argparse
    parser = argparse.ArgumentParser(description="AI Governance Check")
    parser.add_argument("--status", action="store_true", help="Show kill switch and permission status")
    parser.add_argument("--check-agent", type=str, help="Check agent permission level")
    parser.add_argument("--check-action", type=str, help="Action to check (requires --check-agent)")
    parser.add_argument("--enable-kill-switch", type=str, help="Enable global kill switch with reason")
    parser.add_argument("--disable-kill-switch", action="store_true", help="Disable global kill switch")
    args = parser.parse_args()

    if args.enable_kill_switch:
        gov = load_governance()
        gov["kill_switch"]["global_enabled"] = True
        gov["kill_switch"]["reason"] = args.enable_kill_switch
        gov["kill_switch"]["triggered_at"] = datetime.now().isoformat()
        gov["kill_switch"]["triggered_by"] = "cli"
        with open(GOVERNANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(gov, f, ensure_ascii=False, indent=2)
        print(f"KILL SWITCH ENABLED: {args.enable_kill_switch}")
        return

    if args.disable_kill_switch:
        gov = load_governance()
        gov["kill_switch"]["global_enabled"] = False
        gov["kill_switch"]["reason"] = ""
        gov["kill_switch"]["triggered_at"] = None
        with open(GOVERNANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(gov, f, ensure_ascii=False, indent=2)
        print("KILL SWITCH DISABLED")
        return

    if args.check_agent:
        level = get_agent_permission_level(args.check_agent)
        print(f"Agent: {args.check_agent}")
        print(f"Permission Level: {level}")
        if args.check_action:
            is_ok, reason = check_permission(args.check_agent, args.check_action)
            print(f"Action '{args.check_action}': {'GRANTED' if is_ok else 'DENIED'}")
            print(f"Reason: {reason}")
        return

    if args.status:
        is_safe, reason = check_kill_switch()
        print("=== AI Governance Status ===")
        print(f"Kill Switch: {'ACTIVE - ' + reason if not is_safe else 'OK (not active)'}")
        print(f"\nRegistered Agents ({len(list_agents())}):")
        for agent in list_agents():
            print(f"  {agent['permission_level']} | {agent['name']:15s} | {agent['label']}")
        return

    # Default: show status
    is_safe, reason = check_kill_switch()
    print(f"Kill Switch: {'ACTIVE' if not is_safe else 'OK'}")
    print(f"Agents registered: {len(list_agents())}")


if __name__ == "__main__":
    main()
