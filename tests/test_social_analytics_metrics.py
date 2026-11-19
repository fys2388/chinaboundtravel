"""Regression tests for Buffer analytics metric parsing."""
from datetime import datetime, timedelta, timezone

import social_analytics_pull as analytics


def test_posts_query_uses_current_buffer_input_contract(monkeypatch):
    captured = {}

    # 夹具日期动态化：get_published_updates 会过滤掉 sentAt 早于 (now - days) 的帖子，
    # 用固定的历史日期（如 2026-09-13）会随系统时间推移失效。取「当前时间 - 1 天」
    # 保证始终落在 7 天窗口内。
    recent_sent_at = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    monkeypatch.setattr(analytics, "get_organization_id", lambda token: "org-a")
    monkeypatch.setattr(
        analytics,
        "buffer_api_request",
        lambda token, query, variables=None: captured.update(variables or {})
        or {
            "posts": {
                "edges": [
                    {
                        "node": {
                            "id": "post-1",
                            "sentAt": recent_sent_at,
                        }
                    }
                ]
            }
        },
    )

    posts = analytics.get_published_updates("token-account-a-123456", "channel-a")

    assert len(posts) == 1
    assert "status" not in captured["input"]
    assert "since" not in captured["input"]
    assert captured["input"]["filter"] == {
        "status": ["sent"],
        "channelIds": ["channel-a"],
    }
    assert captured["input"]["sort"] == [
        {"field": "dueAt", "direction": "desc"}
    ]


def test_metrics_array_is_used_when_account_has_a_shared_token(monkeypatch):
    for key in (
        "BUFFER_API_TOKEN_A",
        "BUFFER_API_TOKEN_B",
        "BUFFER_ACCESS_TOKEN",
        "BUFFER_ACCESS_TOKEN_2",
        "BUFFER_API_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("BUFFER_API_TOKEN_A", "shared-account-a-123456")

    monkeypatch.setattr(
        analytics,
        "get_channels",
        lambda token: [
            {
                "id": "channel-a",
                "service": "instagram",
                "name": "ChinaBound Travel",
                "stats": {"followers": 100},
            }
        ],
    )
    monkeypatch.setattr(
        analytics,
        "get_published_updates",
        lambda token, channel_id, days: [
            {
                "id": "post-1",
                "text": "China travel guide",
                "sentAt": "2026-09-13T00:00:00Z",
                "metrics": [
                    {"name": "impressions", "value": 120, "unit": "count"},
                    {"name": "clicks", "value": 7, "unit": "count"},
                    {"name": "likes", "value": 9, "unit": "count"},
                ],
            }
        ],
    )

    result = analytics.pull_analytics(days=7, dry_run=True)

    assert result["status"] == "ok"
    assert result["data_source"] == "buffer_api"
    assert result["totals"] == {
        "posts": 1,
        "impressions": 120,
        "clicks": 7,
        "likes": 9,
        "comments": 0,
        "shares": 0,
    }
    assert result["metrics_available_count"] == 1
    assert result["impression_metric_count"] == 1
