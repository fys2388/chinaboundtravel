#!/usr/bin/env python3
"""
ChinaBound Travel - GSC Top20 关键词排名基线报告生成器
拉取最近90天 searchanalytics 数据，生成 Markdown + CSV 报告。
"""
import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# 确保可以 import gsc_utils
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

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

# 日期范围：GSC 有 2-3 天延迟，endDate 取 3 天前
END_DATE = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
START_DATE = (datetime.now() - timedelta(days=92)).strftime("%Y-%m-%d")  # 约90天窗口

SITE_URL = get_site_url()


def fetch_gsc_data():
    """调用 GSC searchanalytics.query 拉取数据"""
    print(f"[INFO] 站点: {SITE_URL}")
    print(f"[INFO] 日期范围: {START_DATE} ~ {END_DATE}")

    # 加载服务账号信息
    sa_info = load_service_account_info()
    if not sa_info:
        print("[ERROR] 无法加载服务账号密钥文件")
        return None, "KEY_NOT_FOUND"

    sa_email = sa_info.get("client_email", "unknown")
    print(f"[INFO] 服务账号: {sa_email}")

    # 构建凭证
    credentials = build_credentials(sa_info)
    if credentials is None:
        print("[ERROR] 无法构建凭证（可能缺少 google-auth 库）")
        return None, "CREDENTIAL_BUILD_FAILED"

    # 构建服务
    try:
        from googleapiclient.discovery import build
        service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
    except Exception as e:
        print(f"[ERROR] 构建 GSC 服务失败: {e}")
        return None, "SERVICE_BUILD_FAILED"

    # 调用 searchanalytics.query
    request_body = {
        "startDate": START_DATE,
        "endDate": END_DATE,
        "dimensions": ["query", "page"],
        "rowLimit": 5000,
    }

    try:
        response = service.searchanalytics().query(
            siteUrl=SITE_URL,
            body=request_body,
        ).execute()
        rows = response.get("rows", [])
        print(f"[INFO] 成功拉取 {len(rows)} 条 query+page 记录")
        return rows, None
    except Exception as e:
        diagnosis = describe_error(e)
        print(f"[ERROR] GSC API 调用失败")
        print(f"  错误码: {diagnosis['code']}")
        print(f"  错误信息: {diagnosis['message']}")
        print(f"  建议: {diagnosis['hint']}")
        print(f"  服务账号邮箱: {sa_email}")
        return None, diagnosis["code"]


def process_data(rows):
    """处理原始数据，返回 DataFrame 和统计信息"""
    import pandas as pd

    records = []
    for row in rows:
        query = row["keys"][0]
        page = row["keys"][1]
        records.append({
            "query": query,
            "page": page,
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": row.get("ctr", 0),
            "position": row.get("position", 0),
        })

    df = pd.DataFrame(records)

    # 按 query 聚合（同一关键词可能对应多个 page，取点击最高的 page）
    # 先按 clicks 降序，保留每个 query 的第一条（即点击最高的 page）
    df_sorted = df.sort_values("clicks", ascending=False)
    df_agg = df_sorted.groupby("query").agg({
        "clicks": "sum",
        "impressions": "sum",
        "position": "mean",  # 平均排名
        "page": "first",  # 点击最高的 page
    }).reset_index()

    # 重新计算 CTR
    df_agg["ctr"] = df_agg.apply(
        lambda r: r["clicks"] / r["impressions"] if r["impressions"] > 0 else 0,
        axis=1,
    )

    # 按点击量降序，点击量相同时按展示量降序（确保零点击时也有意义的排序）
    df_agg = df_agg.sort_values(
        ["clicks", "impressions"], ascending=[False, False]
    ).reset_index(drop=True)

    return df_agg


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

    # === Top5 高展示低点击（高展示 + 零点击/极低CTR）===
    median_impr = df_agg["impressions"].median()
    if avg_ctr > 0:
        ctr_threshold = avg_ctr * 0.5
    else:
        ctr_threshold = 0.01  # 平均CTR为0时，取CTR<1%作为低点击标准
    high_impr_low_click = df_agg[
        (df_agg["impressions"] >= median_impr) &
        (df_agg["ctr"] < ctr_threshold) &
        (df_agg["impressions"] > 0)
    ].sort_values("impressions", ascending=False).head(5)

    # === Top5 排名 4-10 的关键词 ===
    rank_4_10 = df_agg[
        (df_agg["position"] >= 4) & (df_agg["position"] <= 10)
    ].sort_values("impressions", ascending=False).head(5)

    # === 生成 CSV ===
    csv_path = REPORTS_DIR / "keyword-baseline-2026-09.csv"
    # df_agg 列顺序: query, clicks, impressions, position, page, ctr
    csv_df = top20[["query", "position", "impressions", "clicks", "ctr", "page"]].copy()
    csv_df.columns = ["Keyword", "Position", "Impressions", "Clicks", "CTR", "URL"]
    csv_df["Position"] = csv_df["Position"].round(1)
    csv_df["CTR"] = (csv_df["CTR"] * 100).round(2).astype(str) + "%"
    csv_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[INFO] CSV 已保存: {csv_path}")

    # === 生成 Markdown ===
    md_path = REPORTS_DIR / "keyword-baseline-2026-09.md"

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
        # 截断过长的关键词
        kw = row["query"]
        if len(kw) > 60:
            kw = kw[:57] + "..."
        lines.append(f"| {idx+1} | {kw} | {pos} | {impr} | {clicks} | {ctr} | {url} |")

    lines.append("")

    # 优化机会1：高展示低点击
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

    # 优化机会2：排名4-10
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
        lines.append("- 如需补充关键词难度（KD）、搜索量（SV）等数据，请在 .env 中配置 `AHREFS_API_KEY`。")
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

    # 打印摘要到控制台
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


def main():
    print("=" * 60)
    print("  ChinaBound Travel - GSC 关键词基线报告生成器")
    print("=" * 60)
    print()

    rows, error_code = fetch_gsc_data()

    if error_code:
        # 失败处理：输出诊断信息
        sa_info = load_service_account_info()
        sa_email = sa_info.get("client_email", "unknown") if sa_info else "unknown"

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
        print(f"  6. 等待几分钟后重新运行本脚本")

        # 生成失败状态的报告骨架
        md_path = REPORTS_DIR / "keyword-baseline-2026-09.md"
        lines = [
            "# ChinaBound Travel - 关键词排名基线报告",
            "",
            f"- **站点**: {SITE_URL}",
            f"- **数据周期**: {START_DATE} ~ {END_DATE}",
            f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- **完成状态**: 失败（GSC API 不可用）",
            "",
            "## 错误详情",
            "",
            f"- 错误类型: `{error_code}`",
            f"- 服务账号邮箱: `{sa_email}`",
            "",
            "## 需要的手动操作",
            "",
            "1. 登录 [Google Search Console](https://search.google.com/search-console)",
            f"2. 选择属性: `{SITE_URL}`",
            "3. 设置 -> 用户和权限 -> 添加用户",
            f"4. 输入邮箱: `{sa_email}`",
            "5. 权限选择: 完整（Full）",
            "6. 等待几分钟后重新运行报告生成脚本",
            "",
        ]
        md_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n[INFO] 失败报告已保存: {md_path}")
        return 1

    # 处理数据
    df_agg = process_data(rows)

    if len(df_agg) == 0:
        print("[WARN] 没有获取到任何关键词数据")
        return 1

    # 生成报告
    stats = generate_report(df_agg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
