#!/usr/bin/env python3
"""
Social Analytics Pull Engine
Pulls published post metrics from Buffer API and updates metrics files.
Fixes the "all social metrics = 0" issue by adding real data collection.

Usage:
  python scripts/social_analytics_pull.py [--days 7] [--dry-run]

Environment variables (set in GitHub Secrets or .env):
  BUFFER_ACCESS_TOKEN - Buffer API access token (account A: FB+IG+X)
  BUFFER_ACCESS_TOKEN_2 - Buffer API access token (account B: Pinterest)
"""
import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

METRICS_DIR = Path("reports/measurement")
METRICS_DIR.mkdir(parents=True, exist_ok=True)
SOCIAL_DATA_DIR = Path("data/social")
SOCIAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

BUFFER_API_URL = "https://api.buffer.com"


def buffer_api_request(token: str, query: str, variables: dict = None) -> Optional[dict]:
    """Make a Buffer GraphQL API request."""
    url = f"{BUFFER_API_URL}/graphql"
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "chinaboundtravel-analytics/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if "errors" in result:
                print(f"  Buffer API errors: {result['errors'][:2]}")
                return None
            return result.get("data")
    except urllib.error.HTTPError as e:
        print(f"  Buffer API HTTP error: {e.code} {e.reason}")
        return None
    except Exception as e:
        print(f"  Buffer API request failed: {str(e)[:80]}")
        return None


def get_organization_id(token: str) -> str:
    """Get organization ID for the current user via account query."""
    # Try account.organizations (plural)
    query = """
    query GetAccount {
      account {
        id
        name
        organizations {
          id
          name
        }
      }
    }
    """
    data = buffer_api_request(token, query)
    if data and "account" in data:
        account = data["account"]
        # Try to get organizations from account
        if "organizations" in account and account["organizations"]:
            orgs = account["organizations"]
            if orgs:
                org_id = orgs[0].get("id")
                if org_id:
                    print(f"  Got organization ID from account.organizations: {org_id}")
                    return org_id
        # If no organizations, try account ID itself
        account_id = account.get("id")
        if account_id:
            print(f"  Using account ID as org ID: {account_id}")
            return account_id
    
    # Print data for debugging
    if data:
        print(f"  Data keys: {list(data.keys())}")
        if "account" in data:
            print(f"  Account fields: {list(data['account'].keys())}")
            if "organizations" in data["account"]:
                print(f"  Organizations: {data['account']['organizations']}")
    
    return None


def get_channels(token: str) -> list:
    """Get connected social media channels."""
    org_id = get_organization_id(token)
    if not org_id:
        print("  Warning: Could not get organization ID")
        return []
    
    query = """
    query GetChannels($input: ChannelsInput!) {
      channels(input: $input) {
        id
        service
        serviceId
        name
      }
    }
    """
    variables = {
        "input": {
            "organizationId": org_id
        }
    }
    data = buffer_api_request(token, query, variables)
    if data and "channels" in data:
        return data["channels"]
    return []


def get_published_updates(token: str, channel_id: str, days: int = 7) -> list:
    """Get published posts for a channel with analytics (Buffer API v2)."""
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    org_id = get_organization_id(token)
    
    query = """
    query GetPosts($input: PostsInput!) {
      posts(input: $input) {
        edges {
          node {
            id
            text
            channelService
            sentAt
            metrics {
              name
              value
              unit
            }
          }
        }
      }
    }
    """
    variables = {
        "input": {
            "organizationId": org_id,
            "status": "sent",
            "since": since,
            "limit": 100,
        }
    }
    data = buffer_api_request(token, query, variables)
    if data and "posts" in data:
        # Try edges/node format first
        if "edges" in data["posts"]:
            return [edge.get("node", {}) for edge in data["posts"]["edges"]]
        # Fallback to direct posts array
        if "posts" in data["posts"]:
            return data["posts"]["posts"]
        # If it's already an array
        if isinstance(data["posts"], list):
            return data["posts"]
    return []


def validate_buffer_token(token: str, label: str = "unknown") -> bool:
    """Validate Buffer API token by making a simple channels request."""
    if not token:
        print(f"  [{label}] Token not configured")
        return False
    channels = get_channels(token)
    if channels:
        print(f"  [{label}] Token VALID - {len(channels)} channels connected:")
        for ch in channels:
            print(f"    - {ch.get('service', '?')}: {ch.get('name', '?')} ({ch.get('stats', {}).get('followers', 0)} followers)")
        return True
    else:
        print(f"  [{label}] Token INVALID or no channels")
        return False


def pull_analytics(days: int = 7, dry_run: bool = False) -> dict:
    """Pull analytics from all Buffer accounts and compile metrics."""
    token_a = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    token_b = os.environ.get("BUFFER_ACCESS_TOKEN_2", "")

    # IMPORTANT: Do NOT fall back to BUFFER_WORKER_URL - that is a publish endpoint URL,
    # not a Buffer API access token. Using it causes auth failures and all-zero metrics.
    # If tokens are not configured, report clearly instead of silently using wrong credentials.

    def _is_valid_token_format(token: str) -> bool:
        """Basic validation: Buffer API tokens are alphanumeric strings, not URLs."""
        if not token:
            return False
        # Reject URLs, paths, or anything that looks like an endpoint
        if token.startswith("http://") or token.startswith("https://"):
            return False
        if "/" in token or len(token) < 10:
            return False
        return True

    if token_a and not _is_valid_token_format(token_a):
        print(f"  WARNING: BUFFER_ACCESS_TOKEN looks invalid (not a valid API token format). "
              f"Did you accidentally set BUFFER_WORKER_URL?")
        token_a = ""
    if token_b and not _is_valid_token_format(token_b):
        print(f"  WARNING: BUFFER_ACCESS_TOKEN_2 looks invalid (not a valid API token format).")
        token_b = ""

    all_metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "date": date.today().isoformat(),
        "days_covered": days,
        "accounts": {},
        "by_platform": {
            "instagram": {"posts": 0, "impressions": 0, "clicks": 0, "likes": 0, "comments": 0, "shares": 0},
            "facebook": {"posts": 0, "impressions": 0, "clicks": 0, "likes": 0, "comments": 0, "shares": 0},
            "twitter": {"posts": 0, "impressions": 0, "clicks": 0, "likes": 0, "comments": 0, "shares": 0},
            "pinterest": {"posts": 0, "impressions": 0, "clicks": 0, "likes": 0, "comments": 0, "shares": 0},
        },
        "totals": {"posts": 0, "impressions": 0, "clicks": 0, "likes": 0, "comments": 0, "shares": 0},
        "posts": [],
    }

    tokens = [("account_a", token_a), ("account_b", token_b)]
    has_valid_token = False

    for label, token in tokens:
        if not token:
            print(f"  [{label}] No token configured, skipping")
            continue

        print(f"\n  Pulling from {label}...")
        channels = get_channels(token)
        if not channels:
            print(f"  [{label}] No channels found")
            continue

        has_valid_token = True
        account_metrics = {"channels": [], "posts": 0, "impressions": 0, "clicks": 0}

        for channel in channels:
            service = channel.get("service", "").lower()
            platform_map = {
                "instagram": "instagram", "ig": "instagram",
                "facebook": "facebook", "fb": "facebook",
                "twitter": "twitter", "x": "twitter",
                "pinterest": "pinterest",
            }
            platform = platform_map.get(service, service)

            print(f"    Fetching {platform} updates...")
            updates = get_published_updates(token, channel["id"], days)
            print(f"      Found {len(updates)} published updates in last {days} days")

            ch_metrics = {"posts": 0, "impressions": 0, "clicks": 0, "likes": 0, "comments": 0, "shares": 0}
            for update in updates:
                stats = update.get("stats", {})
                impressions = stats.get("impressions", stats.get("reach", 0)) or 0
                clicks = stats.get("clicks", 0) or 0
                likes = stats.get("likes", stats.get("favorites", 0)) or 0
                comments = stats.get("comments", 0) or 0
                shares = stats.get("shares", stats.get("retweets", 0)) or 0

                ch_metrics["posts"] += 1
                ch_metrics["impressions"] += impressions
                ch_metrics["clicks"] += clicks
                ch_metrics["likes"] += likes
                ch_metrics["comments"] += comments
                ch_metrics["shares"] += shares

                all_metrics["posts"].append({
                    "id": update.get("id"),
                    "platform": platform,
                    "text": (update.get("text", "") or "")[:200],
                    "created_at": update.get("createdAt"),
                    "impressions": impressions,
                    "clicks": clicks,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                })

            if platform in all_metrics["by_platform"]:
                for k in ch_metrics:
                    all_metrics["by_platform"][platform][k] += ch_metrics[k]

            for k in ["posts", "impressions", "clicks", "likes", "comments", "shares"]:
                all_metrics["totals"][k] += ch_metrics[k]
                account_metrics[k] = account_metrics.get(k, 0) + ch_metrics[k]

            account_metrics["channels"].append({
                "service": service,
                "name": channel.get("name"),
                "followers": channel.get("stats", {}).get("followers", 0),
                **ch_metrics,
            })

        all_metrics["accounts"][label] = account_metrics

    if not has_valid_token:
        print("\n  WARNING: No valid Buffer tokens found. Analytics will remain at 0.")
        print("  Set BUFFER_ACCESS_TOKEN and BUFFER_ACCESS_TOKEN_2 environment variables.")
        all_metrics["warning"] = "No valid Buffer API tokens configured"

    # Save detailed analytics
    detail_path = SOCIAL_DATA_DIR / f"analytics_{date.today().isoformat()}.json"
    if not dry_run:
        with open(detail_path, "w", encoding="utf-8") as f:
            json.dump(all_metrics, f, indent=2, ensure_ascii=False)
        print(f"\n  Detailed analytics saved: {detail_path}")

    # Update current_metrics.json
    metrics_path = METRICS_DIR / "current_metrics.json"
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            current = json.load(f)
    else:
        current = {"timestamp": "", "date": "", "traffic": {}, "content": {}, "social": {}, "conversion": {}, "revenue": {}, "seo": {}}

    current["timestamp"] = datetime.utcnow().isoformat()
    current["date"] = date.today().isoformat()
    current["social"] = {
        "total_posts": all_metrics["totals"]["posts"],
        "total_impressions": all_metrics["totals"]["impressions"],
        "total_clicks": all_metrics["totals"]["clicks"],
        "total_likes": all_metrics["totals"]["likes"],
        "total_comments": all_metrics["totals"]["comments"],
        "total_shares": all_metrics["totals"]["shares"],
        "by_platform": all_metrics["by_platform"],
        "last_updated": datetime.utcnow().isoformat(),
        "data_source": "buffer_api" if has_valid_token else "unavailable",
    }

    if not dry_run:
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        print(f"  current_metrics.json updated: {all_metrics['totals']['posts']} posts, {all_metrics['totals']['impressions']} impressions")

    return all_metrics


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pull social analytics from Buffer API")
    parser.add_argument("--days", type=int, default=7, help="Days of analytics to pull")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    parser.add_argument("--validate", action="store_true", help="Only validate tokens")
    args = parser.parse_args()

    print("=" * 60)
    print("Social Analytics Pull Engine")
    print("=" * 60)

    if args.validate:
        print("\nValidating Buffer API tokens...")
        token_a = os.environ.get("BUFFER_ACCESS_TOKEN", "")
        token_b = os.environ.get("BUFFER_ACCESS_TOKEN_2", "")
        # Do NOT fall back to BUFFER_WORKER_URL - that's a publish endpoint, not an API token
        valid_a = validate_buffer_token(token_a, "account_a") if token_a else (print("  [account_a] BUFFER_ACCESS_TOKEN not set") or False)
        valid_b = validate_buffer_token(token_b, "account_b") if token_b else (print("  [account_b] BUFFER_ACCESS_TOKEN_2 not set") or False)
        print(f"\nResult: account_a={'VALID' if valid_a else 'MISSING/INVALID'}, account_b={'VALID' if valid_b else 'MISSING/INVALID'}")
        if not (valid_a or valid_b):
            print("\n  💡 To fix: Add Buffer API access tokens to GitHub Secrets:")
            print("     - BUFFER_ACCESS_TOKEN (account A: Facebook + Instagram + X)")
            print("     - BUFFER_ACCESS_TOKEN_2 (account B: Pinterest)")
            print("  ⚠️  Do NOT use BUFFER_WORKER_URL - that is a publish endpoint, not an API token")
        return 0 if (valid_a or valid_b) else 1

    print(f"\nPulling last {args.days} days of analytics...")
    metrics = pull_analytics(days=args.days, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Posts: {metrics['totals']['posts']}")
    print(f"  Impressions: {metrics['totals']['impressions']}")
    print(f"  Clicks: {metrics['totals']['clicks']}")
    print(f"  Likes: {metrics['totals']['likes']}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
