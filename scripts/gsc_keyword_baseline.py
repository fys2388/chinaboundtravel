#!/usr/bin/env python3
"""
ChinaBound Travel - GSC Top20 关键词排名基线报告生成器

拉取最近90天 searchanalytics 数据，生成 Markdown + CSV 报告。

扩展功能（v2）:
  --json       输出原始 JSON 数据到 stdout，供其他脚本消费（不生成报告文件）
  --compare    与上一期基线 CSV 对比，输出排名变化（上升/下降/新关键词）
  --output-dir 自定义报告输出目录

原有功能保持不变：默认生成 reports/keyword-baseline-YYYY-MM.csv 和 .md
"""
import sys
import os
import json
import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path

# 确保可以 import gsc_utils
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from dotenv import load_dotenv  # noqa: E402

from gsc_utils import (
    load_service_account_info,
    build_credentials,
    get_site_url,
    describe_error,
    DEFAULT_SITE_URL,
)

BLOG_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = BLOG_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BLOG_ROOT / ".env")

# 日期范围：GSC 有 2-3 天延迟，endDate 取 3 天前
END_DATE = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
START_DATE = (datetime.now() - timedelta(days=92)).strftime("%Y-%m-%d")  # 约90天窗口

SITE_URL = get_site_url()


# ===========================================================================
# GSC data fetching (importable by other scripts)
# ===========================================================================

def fetch_gsc_data(dimensions=None, start_date=None, end_date=None,
                   row_limit=5000):
    """调用 GSC searchanalytics.query 拉取数据。

    Args:
        dimensions: list of dimension names, default ["query", "page"]
        start_date: YYYY-MM-DD, default 92 days ago
        end_date: YYYY-MM-DD, default 3 days ago
        row_limit: max rows, default 5000

    Returns:
        (rows, error_code) — rows is list of dicts or None on failure
    """
    dimensions = dimensions or ["query", "page"]
    start_date = start_date or START_DATE
    end_date = end_date or END_DATE

    print(f"[INFO] 站点: {SITE_URL}", file=sys.stderr)
    print(f"[INFO] 日期范围: {start_date} ~ {end_date}", file=sys.stderr)
    print(f"[INFO] dimensions: {dimensions}", file=sys.stderr)

    # 加载服务账号信息
    sa_info = load_service_account_info()
    if not sa_info:
        print("[ERROR] 无法加载服务账号密钥文件", file=sys.stderr)
        return None, "KEY_NOT_FOUND"

    sa_email = sa_info.get("client_email", "unknown")
    print(f"[INFO] 服务账号: {sa_email}", file=sys.stderr)

    # 构建凭证
    credentials = build_credentials(sa_info)
    if credentials is None:
        print("[ERROR] 无法构建凭证（可能缺少 google-auth 库）", file=sys.stderr)
        return None, "CREDENTIAL_BUILD_FAILED"

    # 构建服务
    try:
        from googleapiclient.discovery import build
        service = build("searchconsole", "v1", credentials=credentials,
                        cache_discovery=False)
    except Exception as e:
        print(f"[ERROR] 构建 GSC 服务失败: {e}", file=sys.stderr)
        return None, "SERVICE_BUILD_FAILED"

    # 调用 searchanalytics.query
    request_body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }

    try:
        response = service.searchanalytics().query(
            siteUrl=SITE_URL,
            body=request_body,
        ).execute()
        rows = response.get("rows", [])
        print(f"[INFO] 成功拉取 {len(rows)} 条记录", file=sys.stderr)
        return rows, None
    except Exception as e:
        diagnosis = describe_error(e)
        print(f"[ERROR] GSC API 调用失败", file=sys.stderr)
        print(f"  错误码: {diagnosis['code']}", file=sys.stderr)
        print(f"  错误信息: {diagnosis['message']}", file=sys.stderr)
        print(f"  建议: {diagnosis['hint']}", file=sys.stderr)
        return None, diagnosis["code"]


# ===========================================================================
# Data processing
# ===========================================================================

def process_data(rows):
    """处理原始数据，返回 DataFrame 和统计信息"""
    import pandas as pd

    records = []
    for row in rows:
        keys = row.get("keys", [])
        query = keys[0] if len(keys) > 0 else ""
        page = keys[1] if len(keys) > 1 else ""
        records.append({
            "query": query,
            "page": page,
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": row.get("ctr", 0),
            "position": row.get("position", 0),
        })

    df = pd.DataFrame(records)

    if df.empty:
        return df

    # 按 query 聚合（同一关键词可能对应多个 page，取点击最高的 page）
    df_sorted = df.sort_values("clicks", ascending=False)
    df_agg = df_sorted.groupby("query").agg({
        "clicks": "sum",
        "impressions": "sum",
        "position": "mean",
        "page": "first",
    }).reset_index()

    # 重新计算 CTR
    df_agg["ctr"] = df_agg.apply(
        lambda r: r["clicks"] / r["impressions"] if r["impressions"] > 0 else 0,
        axis=1,
    )

    df_agg = df_agg.sort_values(
        ["clicks", "impressions"], ascending=[False, False]
    ).reset_index(drop=True)

    return df_agg


# ===========================================================================
# Baseline comparison
# ===========================================================================

def find_latest_baseline_csv(exclude_current=False):
    """Find the most recent keyword-baseline-*.csv in reports/.

    Returns Path or None.
    """
    pattern = REPORTS_DIR / "keyword-baseline-*.csv"
    candidates = sorted(REPORTS_DIR.glob("keyword-baseline-*.csv"))
    if not candidates:
        return None
    if exclude_current and len(candidates) > 1:
        return candidates[-2]
    return candidates[-1]


def load_baseline_keywords(csv_path):
    """Load a baseline CSV and return {query: {position, impressions, clicks}}."""
    result = {}
    if not csv_path or not Path(csv_path).is_file():
        return result
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                query = (row.get("Keyword") or row.get("query") or "").strip()
                if not query:
                    continue
                try:
                    pos = float(row.get("Position", 0) or 0)
                except ValueError:
                    pos = 0
                try:
                    impr = int(float(row.get("Impressions", 0) or 0))
                except ValueError:
                    impr = 0
                try:
                    clicks = int(float(row.get("Clicks", 0) or 0))
                except ValueError:
                    clicks = 0
                result[query] = {
                    "position": pos,
                    "impressions": impr,
                    "clicks": clicks,
                    "page": row.get("URL", row.get("page", "")),
                }
    except Exception as exc:
        print(f"[WARN] Could not parse baseline {csv_path}: {exc}",
              file=sys.stderr)
    return result


def compare_with_baseline(df_agg, baseline_csv=None):
    """Compare current keywords with previous baseline.

    Returns dict with keys: new_keywords, rank_improved, rank_dropped,
    stable, all with list of dicts.
    """
    if baseline_csv is None:
        baseline_csv = find_latest_baseline_csv(exclude_current=True)
    baseline = load_baseline_keywords(baseline_csv)

    new_keywords = []
    rank_improved = []
    rank_dropped = []
    stable = []

    for _, row in df_agg.iterrows():
        query = row["query"]
        current_pos = row["position"]
        entry = {
            "query": query,
            "page": row["page"],
            "position": round(current_pos, 1),
            "impressions": int(row["impressions"]),
            "clicks": int(row["clicks"]),
            "ctr": round(row["ctr"], 4),
        }
        if query not in baseline:
            entry["previous_position"] = None
            new_keywords.append(entry)
        else:
            prev = baseline[query]["position"]
            entry["previous_position"] = prev
            delta = prev - current_pos  # positive = improved (lower position number)
            entry["delta"] = round(delta, 1)
            if delta > 2:
                rank_improved.append(entry)
            elif delta < -2:
                rank_dropped.append(entry)
            else:
                stable.append(entry)

    # Sort
    new_keywords.sort(key=lambda x: x["impressions"], reverse=True)
    rank_improved.sort(key=lambda x: x["delta"], reverse=True)
    rank_dropped.sort(key=lambda x: x["delta"])

    return {
        "baseline_file": str(baseline_csv) if baseline_csv else None,
        "new_keywords": new_keywords,
        "rank_improved": rank_improved,
        "rank_dropped": rank_dropped,
        "stable": stable,
    }


# ===========================================================================
# JSON output mode
# ===========================================================================

def output_json(df_agg, comparison=None):
    """Output raw data as JSON to stdout for other scripts to consume."""
    records = []
    for _, row in df_agg.iterrows():
        records.append({
            "query": row["query"],
            "page": row["page"],
            "clicks": int(row["clicks"]),
            "impressions": int(row["impressions"]),
            "ctr": round(float(row["ctr"]), 4),
            "position": round(float(row["position"]), 1),
        })

    output = {
        "site_url": SITE_URL,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "generated_at": datetime.now().isoformat(),
        "total_keywords": len(records),
        "total_impressions": int(df_agg["impressions"].sum()),
        "total_clicks": int(df_agg["clicks"].sum()),
        "avg_position": round(float(df_agg["position"].mean()), 1),
        "keywords": records,
    }

    if comparison:
        output["comparison"] = {
            "baseline_file": comparison["baseline_file"],
            "new_keywords_count": len(comparison["new_keywords"]),
            "rank_improved_count": len(comparison["rank_improved"]),
            "rank_dropped_count": len(comparison["rank_dropped"]),
            "new_keywords": comparison["new_keywords"][:50],
            "rank_dropped": comparison["rank_dropped"][:50],
            "rank_improved": comparison["rank_improved"][:50],
        }

    print(json.dumps(output, indent=2, ensure_ascii=False))


# ===========================================================================
# Report generation (original functionality, preserved)
# ===========================================================================

def generate_report(df_agg):
    """生成 Markdown 报告和 CSV"""
    import pandas as pd

    # === 汇总统计 ===
    total_impressions = int(df_agg["impressions"].sum())
    total_clicks = int(df_agg["clicks"].sum())
    avg_position = df_agg["position"].mean()
    avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0

    # === Top20 ===
    top20 = df_agg.head(20).copy()

    # === Top5 高展示低点击 ===
    median_impr = df_agg["impressions"].median()
    if avg_ctr > 0:
        ctr_threshold = avg_ctr * 0.5
    else:
        ctr_threshold = 0.01
    high_impr_low_click = df_agg[
        (df_agg["impressions"] >= median_impr) &
        (df_agg["ctr"] < ctr_threshold) &
        (df_agg["impressions"] > 0)
    ].sort_values("impressions", ascending=False).head(5)

    # === Top5 排名 4-10 ===
    rank_4_10 = df_agg[
        (df_agg["position"] >= 4) & (df_agg["position"] <= 10)
    ].sort_values("impressions", ascending=False).head(5)

    # === 生成 CSV ===
    month_str = datetime.now().strftime("%Y-%m")
    csv_path = REPORTS_DIR / f"keyword-baseline-{month_str}.csv"
    csv_df = top20[["query", "position", "impressions", "clicks", "ctr", "page"]].copy()
    csv_df.columns = ["Keyword", "Position", "Impressions", "Clicks", "CTR", "URL"]
    csv_df["Position"] = csv_df["Position"].round(1)
    csv_df["CTR"] = (csv_df["CTR"] * 100).round(2).astype(str) + "%"
    csv_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[INFO] CSV 已保存: {csv_path}")

    # === 生成 Markdown ===
    md_path = REPORTS_DIR / f"keyword-baseline-{month_str}.md"

    lines = []
    lines.append("# ChinaBound Travel - 关键词排名基线报告")
    lines.append("")
    lines.append(f"- **站点**: {SITE_URL}")
    lines.append(f"- **数据周期**: {START_DATE} ~ {END_DATE}（最近90天）")
    lines.append(f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- **数据源**: Google Search Console API (searchanalytics.query)")
    lines.append(f"- **完成状态**: 成功")
    lines.append("")

    # 汇总统计
    lines.append("## 一、汇总统计")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总展示量 (Impressions) | {total_impressions:,} |")
    lines.append(f"| 总点击量 (Clicks) | {total_clicks:,} |")
    lines.append(f"| 平均排名 (Avg Position) | {avg_position:.1f} |")
    lines.append(f"| 平均点击率 (Avg CTR) | {avg_ctr*100:.2f}% |")
    lines.append(f"| 有数据关键词总数 | {len(df_agg):,} |")
    lines.append("")

    # Top20 表格
    lines.append("## 二、Top20 关键词排名基线")
    lines.append("")
    lines.append("| # | 关键词 (Keyword) | 排名 (Position) | 展示量 (Impressions) | 点击量 (Clicks) | 点击率 (CTR) | 目标URL |")
    lines.append("|---|-------------------|-----------------|----------------------|-----------------|--------------|---------|")

    for idx, row in top20.iterrows():
        pos = f"{row['position']:.1f}"
        impr = f"{int(row['impressions']):,}"
        clicks = f"{int(row['clicks']):,}"
        ctr = f"{row['ctr']*100:.2f}%"
        url = row["page"]
        kw = row["query"]
        if len(kw) > 60:
            kw = kw[:57] + "..."
        lines.append(f"| {idx+1} | {kw} | {pos} | {impr} | {clicks} | {ctr} | {url} |")

    lines.append("")

    # 优化机会1
    lines.append("## 三、优化机会分析")
    lines.append("")
    lines.append("### 3.1 Top5 高展示低点击关键词（标题/摘要优化机会）")
    lines.append("")
    if len(high_impr_low_click) > 0:
        lines.append("| # | 关键词 | 排名 | 展示量 | 点击量 | CTR | 目标URL |")
        lines.append("|---|--------|------|--------|--------|-----|---------|")
        for i, (_, row) in enumerate(high_impr_low_click.iterrows(), 1):
            kw = row["query"]
            if len(kw) > 50:
                kw = kw[:47] + "..."
            lines.append(f"| {i} | {kw} | {row['position']:.1f} | {int(row['impressions']):,} | {int(row['clicks']):,} | {row['ctr']*100:.2f}% | {row['page']} |")
    else:
        lines.append("无符合条件的关键词。")
    lines.append("")

    # 优化机会2
    lines.append("### 3.2 Top5 排名 4-10 关键词（可提升到前3的机会）")
    lines.append("")
    if len(rank_4_10) > 0:
        lines.append("| # | 关键词 | 排名 | 展示量 | 点击量 | CTR | 目标URL |")
        lines.append("|---|--------|------|--------|--------|-----|---------|")
        for i, (_, row) in enumerate(rank_4_10.iterrows(), 1):
            kw = row["query"]
            if len(kw) > 50:
                kw = kw[:47] + "..."
            lines.append(f"| {i} | {kw} | {row['position']:.1f} | {int(row['impressions']):,} | {int(row['clicks']):,} | {row['ctr']*100:.2f}% | {row['page']} |")
    else:
        lines.append("无符合条件的关键词。")
    lines.append("")

    # Ahrefs 说明
    lines.append("### 3.3 Ahrefs API 状态")
    lines.append("")
    ahrefs_key = os.environ.get("AHREFS_API_KEY", "")
    if ahrefs_key:
        lines.append("- Ahrefs API Key 已配置，可补充关键词难度（KD）和搜索量数据。")
    else:
        lines.append("- **未检测到 AHREFS_API_KEY**，本报告仅基于 GSC 数据。")
    lines.append("")

    # 行动建议
    lines.append("## 四、行动建议")
    lines.append("")
    lines.append("1. **高展示低点击词**：优化 meta title 和 meta description，提升 CTR。")
    lines.append("2. **排名 4-10 的词**：加强内容深度、内链建设和外链，争取进入前3。")
    lines.append("3. **Top20 核心词**：持续监控排名波动，保持内容更新。")
    lines.append("4. **零点击高展示词**：考虑是否搜索意图不匹配，调整内容方向。")
    lines.append("")

    md_content = "\n".join(lines)
    md_path.write_text(md_content, encoding="utf-8")
    print(f"[INFO] Markdown 已保存: {md_path}")

    # 打印摘要
    print("\n" + "=" * 60)
    print("  报告摘要")
    print("=" * 60)
    print(f"  总展示量: {total_impressions:,}")
    print(f"  总点击量: {total_clicks:,}")
    print(f"  平均排名: {avg_position:.1f}")
    print(f"  平均CTR:  {avg_ctr*100:.2f}%")
    print(f"  关键词数: {len(df_agg):,}")
    print("=" * 60)

    return {
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "avg_position": avg_position,
        "avg_ctr": avg_ctr,
        "keyword_count": len(df_agg),
        "top20": top20,
        "high_impr_low_click": high_impr_low_click,
        "rank_4_10": rank_4_10,
    }


# ===========================================================================
# Main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ChinaBound Travel GSC keyword baseline generator"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output raw JSON data to stdout (no report files)"
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="Compare with previous baseline and include rank changes"
    )
    parser.add_argument(
        "--baseline", type=str, default=None,
        help="Path to specific baseline CSV for comparison"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  ChinaBound Travel - GSC 关键词基线报告生成器")
    print("=" * 60)
    print()

    rows, error_code = fetch_gsc_data()

    if error_code:
        sa_info = load_service_account_info()
        sa_email = sa_info.get("client_email", "unknown") if sa_info else "unknown"

        if args.json_output:
            print(json.dumps({
                "error": error_code,
                "site_url": SITE_URL,
                "service_account": sa_email,
            }))
            return 1

        print("\n[FAIL] GSC API 不可用，无法生成数据报告。")
        print(f"  错误类型: {error_code}")
        print(f"  服务账号邮箱: {sa_email}")
        print()
        print("需要的手动操作:")
        print(f"  1. 登录 Google Search Console: https://search.google.com/search-console")
        print(f"  2. 选择属性: {SITE_URL}")
        print(f"  3. 设置 -> 用户和权限 -> 添加用户")
        print(f"  4. 输入邮箱: {sa_email}")
        print(f"  5. 权限选择: 完整（Full）")
        return 1

    df_agg = process_data(rows)

    if len(df_agg) == 0:
        print("[WARN] 没有获取到任何关键词数据")
        if args.json_output:
            print(json.dumps({"keywords": [], "total_keywords": 0}))
        return 1

    # Baseline comparison
    comparison = None
    if args.compare or args.json_output:
        baseline_path = args.baseline
        if baseline_path:
            comparison = compare_with_baseline(df_agg, Path(baseline_path))
        else:
            comparison = compare_with_baseline(df_agg)
        if comparison and args.compare:
            print(f"\n[COMPARE] Baseline: {comparison['baseline_file']}")
            print(f"  新关键词: {len(comparison['new_keywords'])}")
            print(f"  排名上升: {len(comparison['rank_improved'])}")
            print(f"  排名下降: {len(comparison['rank_dropped'])}")
            print(f"  稳定: {len(comparison['stable'])}")

    # JSON output mode
    if args.json_output:
        output_json(df_agg, comparison)
        return 0

    # Default: generate report files
    stats = generate_report(df_agg)

    # If --compare, also print comparison summary
    if comparison:
        print("\n[基线对比]")
        print(f"  对比基线: {comparison['baseline_file']}")
        print(f"  新进入关键词: {len(comparison['new_keywords'])}")
        if comparison['new_keywords']:
            for kw in comparison['new_keywords'][:5]:
                print(f"    + {kw['query']} (pos={kw['position']}, impr={kw['impressions']})")
        print(f"  排名下降 >2: {len(comparison['rank_dropped'])}")
        if comparison['rank_dropped']:
            for kw in comparison['rank_dropped'][:5]:
                print(f"    - {kw['query']}: {kw['previous_position']:.1f} -> {kw['position']:.1f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
