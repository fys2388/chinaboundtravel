#!/usr/bin/env python3
"""Merge every quality signal into one issue list for the ops dashboard."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}
OWNER_BY_SOURCE = {
    "content": "content",
    "predeploy": "engineering",
    "site": "seo",
    "visual": "engineering",
    "seo": "seo",
}

CONTENT_CHECK_ACTIONS = {
    "quality_validator": "修复报告中的乱码、编码、front matter 或媒体合规问题后重跑内容质量巡检。",
    "content_id": "修复缺失、重复或格式不合法的 content_id，禁止在发布流程中随机生成。",
    "fact_guard": "核对签证、价格、交通等动态事实，并补充可追溯来源。",
    "brand_audit": "移除旧人设和虚构亲历表达，统一为当前 Editorial Voice。",
    "trust_audit": "检查内容信任审计报告，补充引用、来源或必要的编辑说明。",
}


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_issue(issue: dict, source: str, detected_at: str) -> dict:
    severity = str(issue.get("severity", "P2")).upper()
    if severity not in SEVERITY_ORDER:
        severity = "P2"
    owner = (
        issue.get("owner")
        or issue.get("assigned_to")
        or issue.get("agent")
        or OWNER_BY_SOURCE.get(source, "operations")
    )
    return {
        "id": issue.get("id")
        or f"{source}-{abs(hash((source, issue.get('type'), issue.get('page')))):x}",
        "severity": severity,
        "source": source,
        "type": issue.get("type", "unknown"),
        "title": issue.get("title") or issue.get("message") or issue.get("type", "Issue"),
        "page": issue.get("page") or issue.get("file") or "",
        "evidence": issue.get("evidence") or issue.get("message") or "",
        "recommended_action": issue.get("recommended_action")
        or issue.get("resolution_note")
        or "Review and remediate the reported issue.",
        "owner": owner,
        "status": issue.get("status") or "open",
        "first_seen": issue.get("first_seen") or detected_at,
        "last_seen": detected_at,
    }


def issues_from_internal_links(report: dict, detected_at: str) -> list[dict]:
    issues: list[dict] = []
    for link in report.get("links", []):
        status = link.get("status")
        if status not in ("404", "301"):
            continue
        severity = "P1" if status == "404" else "P2"
        issues.append(
            normalize_issue(
                {
                    "id": f"internal-{status}-{link.get('source')}-{link.get('line')}-{link.get('target')}",
                    "severity": severity,
                    "type": "broken_internal_link" if status == "404" else "internal_link_redirect",
                    "title": "Broken internal link" if status == "404" else "Internal link redirect",
                    "page": link.get("source", ""),
                    "evidence": f"{link.get('target', '')} -> HTTP {status}",
                    "recommended_action": (
                        "Update the link or add a redirect."
                        if status == "404"
                        else "Link directly to the final URL."
                    ),
                    "owner": "seo",
                },
                "seo",
                detected_at,
            )
        )
    for malformed in report.get("malformed_list", []):
        issues.append(
            normalize_issue(
                {
                    "id": f"internal-malformed-{malformed.get('source')}-{malformed.get('line')}-{malformed.get('kind')}",
                    "severity": "P1",
                    "type": "malformed_link",
                    "title": f"Malformed link: {malformed.get('kind', 'unknown')}",
                    "page": malformed.get("source", ""),
                    "evidence": malformed.get("snippet", ""),
                    "recommended_action": "Fix the Markdown link syntax.",
                    "owner": "seo",
                },
                "seo",
                detected_at,
            )
        )
    return issues


def issues_from_site_health(report: dict, detected_at: str) -> list[dict]:
    severity_map = {"critical": "P0", "high": "P1", "medium": "P2", "low": "P2"}
    resolved = {"resolved", "fixed", "false_positive", "closed"}
    issues: list[dict] = []
    for issue in report.get("issues", []):
        if str(issue.get("status", "")).lower() in resolved:
            continue
        issues.append(
            normalize_issue(
                {
                    **issue,
                    "severity": severity_map.get(
                        str(issue.get("severity", "")).lower(), "P2"
                    ),
                    "title": issue.get("type", "site health issue"),
                },
                "site_health",
                detected_at,
            )
        )
    return issues


def issues_from_content_audit(
    report: dict,
    validator_report: dict | None,
    detected_at: str,
) -> list[dict]:
    issues: list[dict] = []

    for check in report.get("checks", []):
        exit_code = check.get("exit_code")
        if exit_code in (0, None):
            continue
        blocking = bool(check.get("blocking"))
        check_id = str(check.get("id") or "content_check")
        issues.append(
            normalize_issue(
                {
                    "id": f"content-check-{check_id}-failed",
                    "severity": "P0" if blocking else "P2",
                    "type": f"content_{check_id}_failed",
                    "title": f"{check.get('name', check_id)}未通过",
                    "page": "content/posts",
                    "evidence": (
                        f"{check.get('script', check_id)} exit code={exit_code}; "
                        f"run_id={report.get('run_id', '')}"
                    ),
                    "recommended_action": CONTENT_CHECK_ACTIONS.get(
                        check_id, "查看内容质量巡检报告并修复失败检查项。"
                    ),
                    "owner": check.get("agent") or "content",
                },
                "content",
                detected_at,
            )
        )

    content = report.get("content", {})
    for file_name in content.get("mojibake_files", []):
        issues.append(
            normalize_issue(
                {
                    "id": f"content-mojibake-{file_name}",
                    "severity": "P0",
                    "type": "mojibake",
                    "title": "文章检测到 P0 乱码",
                    "page": file_name,
                    "evidence": "content_quality_validator detected mojibake byte patterns",
                    "recommended_action": "修复文章编码并确认文件保存为无 BOM 的 UTF-8。",
                    "owner": "content",
                },
                "content",
                detected_at,
            )
        )
    for file_name in content.get("encoding_error_files", []):
        issues.append(
            normalize_issue(
                {
                    "id": f"content-encoding-{file_name}",
                    "severity": "P0",
                    "type": "encoding_error",
                    "title": "文章不是合法 UTF-8",
                    "page": file_name,
                    "evidence": "content_quality_validator reported UnicodeDecodeError",
                    "recommended_action": "按原语言恢复文件内容并保存为无 BOM 的 UTF-8。",
                    "owner": "content",
                },
                "content",
                detected_at,
            )
        )

    if not validator_report:
        return issues

    for result in validator_report.get("results", []):
        file_name = result.get("file") or "unknown"

        if not result.get("frontmatter_ok", True):
            issues.append(
                normalize_issue(
                    {
                        "id": f"content-frontmatter-{file_name}",
                        "severity": "P0",
                        "type": "invalid_frontmatter",
                        "title": "文章 front matter 无法解析",
                        "page": file_name,
                        "evidence": "content_quality_validator could not parse front matter",
                        "recommended_action": "修复 front matter 分隔符或首部 BOM，确保正文可正常构建。",
                        "owner": "content",
                    },
                    "content",
                    detected_at,
                )
            )

        if result.get("frontmatter_ok", True) and not result.get("content_id_ok", True):
            issues.append(
                normalize_issue(
                    {
                        "id": f"content-id-{file_name}",
                        "severity": "P1",
                        "type": "missing_content_id",
                        "title": "文章缺少 content_id",
                        "page": file_name,
                        "evidence": "content_id is missing or empty",
                        "recommended_action": "补入稳定且唯一的 content_id，禁止随机生成。",
                        "owner": "content",
                    },
                    "content",
                    detected_at,
                )
            )

        for issue_type, values, severity, action in (
            ("brand_violation", result.get("brand_issues", []), "P1", "移除旧人设或虚构亲历表达。"),
            ("unverified_fact", result.get("fact_issues", []), "P1", "补充官方来源或最后核验日期。"),
        ):
            if not values:
                continue
            issues.append(
                normalize_issue(
                    {
                        "id": f"content-{issue_type}-{file_name}",
                        "severity": severity,
                        "type": issue_type,
                        "title": "品牌表达违规" if issue_type == "brand_violation" else "动态事实缺少核验提示",
                        "page": file_name,
                        "evidence": ", ".join(str(value) for value in values[:5]),
                        "recommended_action": action,
                        "owner": "content",
                    },
                    "content",
                    detected_at,
                )
            )

        media_issues = result.get("media_issues", [])
        if media_issues:
            has_p0_media = any(
                value.startswith("blocked_ai_image_domain:")
                or value.startswith("body_blocked_ai_image:")
                for value in media_issues
            )
            severity = "P0" if has_p0_media else (
                "P1" if "missing_cover" in media_issues else "P2"
            )
            issues.append(
                normalize_issue(
                    {
                        "id": f"content-media-{file_name}",
                        "severity": severity,
                        "type": "media_compliance",
                        "title": "文章媒体资源不符合发布规则",
                        "page": file_name,
                        "evidence": ", ".join(str(value) for value in media_issues[:5]),
                        "recommended_action": "替换违规图片、补齐封面或改用本站允许的媒体地址。",
                        "owner": "content",
                    },
                    "content",
                    detected_at,
                )
            )

        seo_issues = result.get("seo_issues", [])
        if seo_issues:
            issues.append(
                normalize_issue(
                    {
                        "id": f"content-seo-{file_name}",
                        "severity": "P2",
                        "type": "content_seo",
                        "title": "文章 SEO 字段或结构需要优化",
                        "page": file_name,
                        "evidence": ", ".join(str(value) for value in seo_issues[:5]),
                        "recommended_action": "修正标题、描述长度和正文标题层级。",
                        "owner": "content",
                    },
                    "content",
                    detected_at,
                )
            )

    return issues


def load_source_issues(root: Path, detected_at: str) -> tuple[list[dict], dict]:
    issues: list[dict] = []
    source_summary: dict[str, dict] = {}

    source_files = {
        "predeploy": root / "reports/quality/predeploy_quality.json",
        "site": root / "reports/quality/site_audit.json",
        "visual": root / "reports/quality/visual_audit.json",
    }
    for source, path in source_files.items():
        report = read_json(path)
        if report is None:
            source_summary[source] = {"available": False, "issues": 0}
            continue
        current = [
            normalize_issue(issue, source, detected_at)
            for issue in report.get("issues", [])
        ]
        issues.extend(current)
        source_summary[source] = {
            "available": True,
            "generated_at": report.get("generated_at", ""),
            "issues": len(current),
            "P0": sum(1 for issue in current if issue["severity"] == "P0"),
            "P1": sum(1 for issue in current if issue["severity"] == "P1"),
            "P2": sum(1 for issue in current if issue["severity"] == "P2"),
        }

    content_report = read_json(
        root / "reports/content_audit/latest_quality_result.json"
    )
    if content_report is None:
        source_summary["content"] = {"available": False, "issues": 0}
    else:
        validator_report = read_json(
            root / "reports/content_audit/validator_output.json"
        )
        current = issues_from_content_audit(
            content_report, validator_report, detected_at
        )
        issues.extend(current)
        source_summary["content"] = {
            "available": True,
            "generated_at": content_report.get("generated_at", ""),
            "issues": len(current),
            "P0": sum(1 for issue in current if issue["severity"] == "P0"),
            "P1": sum(1 for issue in current if issue["severity"] == "P1"),
            "P2": sum(1 for issue in current if issue["severity"] == "P2"),
        }

    internal_report = read_json(root / "docs/internal_link_audit.json")
    if internal_report is None:
        source_summary["seo"] = {"available": False, "issues": 0}
    else:
        current = issues_from_internal_links(internal_report, detected_at)
        issues.extend(current)
        source_summary["seo"] = {
            "available": True,
            "issues": len(current),
            "P0": sum(1 for issue in current if issue["severity"] == "P0"),
            "P1": sum(1 for issue in current if issue["severity"] == "P1"),
            "P2": sum(1 for issue in current if issue["severity"] == "P2"),
        }

    health_files = sorted(
        path
        for path in (root / "reports/site_health").glob("site_health_*.json")
        if "audit" not in path.name
    )
    health_report = read_json(health_files[-1]) if health_files else None
    if health_report is None:
        source_summary["site_health"] = {"available": False, "issues": 0}
    else:
        current = issues_from_site_health(health_report, detected_at)
        issues.extend(current)
        source_summary["site_health"] = {
            "available": True,
            "generated_at": health_report.get("timestamp", ""),
            "issues": len(current),
            "P0": sum(1 for issue in current if issue["severity"] == "P0"),
            "P1": sum(1 for issue in current if issue["severity"] == "P1"),
            "P2": sum(1 for issue in current if issue["severity"] == "P2"),
        }

    return issues, source_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/quality/quality_issues.json")
    parser.add_argument(
        "--history", default="reports/quality/quality_history.json"
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    detected_at = now_iso()
    output = Path(args.output)
    history_path = Path(args.history)
    previous_report = read_json(output) or {}
    previous_first_seen = {
        issue.get("id"): issue.get("first_seen")
        for issue in previous_report.get("issues", [])
    }

    issues, source_summary = load_source_issues(ROOT, detected_at)
    for issue in issues:
        issue["first_seen"] = previous_first_seen.get(
            issue["id"], issue["first_seen"]
        )

    deduplicated: dict[str, dict] = {}
    for issue in issues:
        existing = deduplicated.get(issue["id"])
        if existing is None:
            deduplicated[issue["id"]] = issue
            continue
        if SEVERITY_ORDER[issue["severity"]] < SEVERITY_ORDER[existing["severity"]]:
            deduplicated[issue["id"]] = issue

    issues = sorted(
        deduplicated.values(),
        key=lambda item: (
            SEVERITY_ORDER[item["severity"]],
            item["source"],
            item["type"],
            item["page"],
        ),
    )
    severity_counts = Counter(issue["severity"] for issue in issues)
    source_counts = Counter(issue["source"] for issue in issues)
    owner_counts = Counter(issue["owner"] for issue in issues)
    summary = {
        "total": len(issues),
        "P0": severity_counts.get("P0", 0),
        "P1": severity_counts.get("P1", 0),
        "P2": severity_counts.get("P2", 0),
        "by_source": dict(source_counts),
        "by_owner": dict(owner_counts),
    }
    report = {
        "generated_at": detected_at,
        "summary": summary,
        "sources": source_summary,
        "issues": issues,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    history = read_json(history_path) or {"version": 1, "snapshots": []}
    snapshots = history.setdefault("snapshots", [])
    previous_ids = set(
        snapshots[-1].get("issue_ids", [])) if snapshots else set()
    current_ids = {issue["id"] for issue in issues}
    snapshots.append(
        {
            "timestamp": detected_at,
            "summary": summary,
            "issue_ids": sorted(current_ids),
            "opened": len(current_ids - previous_ids),
            "resolved": len(previous_ids - current_ids),
        }
    )
    history["version"] = 1
    history["updated_at"] = detected_at
    history["snapshots"] = snapshots[-365:]
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        "quality issues: "
        f"total={summary['total']} P0={summary['P0']} "
        f"P1={summary['P1']} P2={summary['P2']}"
    )
    print(f"wrote {output.as_posix()}")
    if args.strict:
        blocking = summary["P0"] + summary["P1"]
        return int(blocking > 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
