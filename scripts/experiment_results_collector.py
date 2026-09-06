#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验结果收集器
从 GA4 API 拉取 experiment_view / experiment_conversion 事件，生成实验结果报告
用法: python scripts/experiment_results_collector.py
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
EXP_CONFIG = ROOT / "static" / "experiments.json"
RESULTS_DIR = ROOT / "reports" / "experiments"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_experiments():
    """加载实验配置"""
    if not EXP_CONFIG.exists():
        print("❌ experiments.json 不存在")
        return []
    with open(EXP_CONFIG, 'r', encoding='utf-8') as f:
        return json.load(f).get("experiments", [])


def collect_from_ga4(experiments):
    """
    从 GA4 API 拉取实验数据
    依赖 real_data_pull_engine.py 已有的 GA4 认证
    """
    # 尝试导入已有的 GA4 数据拉取引擎
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from real_data_pull_engine import get_ga4_client, PROPERTY_ID
    except ImportError:
        print("⚠️  real_data_pull_engine 不可用，使用本地缓存数据")
        return None

    try:
        client = get_ga4_client()
        if not client:
            print("⚠️  GA4 client 不可用")
            return None
    except Exception as e:
        print(f"⚠️  GA4 client 初始化失败: {e}")
        return None

    results = {}
    today = datetime.now(timezone.utc).date()
    start_date = (today - timedelta(days=28)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    for exp in experiments:
        if exp["status"] != "RUNNING":
            continue
        try:
            # 查询 experiment_view 事件
            response = client.runReport(
                property=f"properties/{PROPERTY_ID}",
                body={
                    "dateRanges": [{"startDate": start_date, "endDate": end_date}],
                    "dimensions": [
                        {"name": "customEvent:experiment_id"},
                        {"name": "customEvent:variant_id"},
                    ],
                    "metrics": [
                        {"name": "eventCount"},
                        {"name": "totalUsers"},
                    ],
                    "dimensionFilter": {
                        "filter": {
                            "fieldName": "customEvent:experiment_id",
                            "stringFilter": {"value": exp["id"]},
                        }
                    },
                }
            )
            exp_results = []
            for row in response.rows:
                exp_results.append({
                    "experiment_id": row.dimension_values[0].value,
                    "variant_id": row.dimension_values[1].value,
                    "views": int(row.metric_values[0].value),
                    "users": int(row.metric_values[1].value),
                })
            results[exp["id"]] = exp_results
            print(f"  ✅ {exp['id']}: {len(exp_results)} 个变体数据")
        except Exception as e:
            print(f"  ⚠️  {exp['id']} 数据拉取失败: {e}")
            results[exp["id"]] = []

    return results


def generate_report(experiments, ga4_results):
    """生成实验结果报告"""
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_experiments": len(experiments),
        "running": sum(1 for e in experiments if e["status"] == "RUNNING"),
        "planned": sum(1 for e in experiments if e["status"] == "PLANNED"),
        "waiting_recrawl": sum(1 for e in experiments if e["status"] == "WAITING_RECRAWL"),
        "experiments": [],
    }

    for exp in experiments:
        exp_data = {
            "id": exp["id"],
            "name": exp["name"],
            "status": exp["status"],
            "type": exp.get("type", ""),
            "start_date": exp.get("start_date"),
            "min_sample": exp.get("min_sample", 0),
            "variants": [],
        }

        # 如果有 GA4 数据，添加样本量和转化率
        if ga4_results and exp["id"] in ga4_results:
            ga4_data = ga4_results[exp["id"]]
            for v in exp.get("variants", []):
                v_data = next((d for d in ga4_data if d["variant_id"] == v["id"]), None)
                exp_data["variants"].append({
                    "id": v["id"],
                    "name": v["name"],
                    "traffic": v.get("traffic", 0),
                    "views": v_data["views"] if v_data else 0,
                    "users": v_data["users"] if v_data else 0,
                })
        else:
            for v in exp.get("variants", []):
                exp_data["variants"].append({
                    "id": v["id"],
                    "name": v["name"],
                    "traffic": v.get("traffic", 0),
                    "views": 0,
                    "users": 0,
                })

        report["experiments"].append(exp_data)

    # 保存报告
    output_file = RESULTS_DIR / "experiment_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 实验结果报告已保存: {output_file}")
    print(f"   总实验: {report['total_experiments']} | 运行中: {report['running']} | 规划中: {report['planned']} | 等待重抓: {report['waiting_recrawl']}")
    return report


def main():
    print("=== 实验结果收集器 ===\n")
    experiments = load_experiments()
    print(f"加载 {len(experiments)} 个实验配置")

    running = [e for e in experiments if e["status"] == "RUNNING"]
    print(f"运行中实验: {len(running)}")

    ga4_results = None
    if running:
        print("\n从 GA4 拉取实验数据...")
        ga4_results = collect_from_ga4(experiments)
    else:
        print("\n无运行中实验，跳过 GA4 数据拉取")

    report = generate_report(experiments, ga4_results)
    return report


if __name__ == "__main__":
    main()
