#!/usr/bin/env python3
"""
Trip Planner Analytics - 分析 AI 行程规划器使用数据

功能：
1. 从 CF KV 读取调用记录
2. 统计分析（城市偏好、时长分布、兴趣分布）
3. 生成周报（选题反哺）
4. 导出 CSV

使用：
    python scripts/trip_planner_analytics.py
    python scripts/trip_planner_analytics.py --week 2026-09-20
    python scripts/trip_planner_analytics.py --export-csv reports/trip_planner_report.csv

@author Joran - ChinaBound Travel
@version 1.0.0
"""

import json
import os
import sys
import io
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path

# Windows 编码修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============ 配置 ============

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "trip-planner"
KV_ENDPOINT = os.environ.get("CF_KV_ENDPOINT", "https://api.cloudflare.com/client/v4")
KV_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
KV_API_TOKEN = os.environ.get("CF_API_TOKEN")
KV_NAMESPACE_ID = "a20785ef5e594755ba1d21850de25593"

# ============ 主函数 ============

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Trip Planner Analytics")
    parser.add_argument("--week", type=str, default=None, 
                       help="分析指定周（格式：2026-09-20）")
    parser.add_argument("--days", type=int, default=7,
                       help="分析最近 N 天（默认：7）")
    parser.add_argument("--export-csv", type=str, default=None,
                       help="导出 CSV 到指定路径")
    parser.add_argument("--local", action="store_true",
                       help="使用本地缓存数据（不连接 CF）")
    
    args = parser.parse_args()
    
    # 确保报告目录存在
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 获取数据
    if args.local:
        data = load_local_data(args.days)
    else:
        data = fetch_cf_data(args.days)
    
    if not data:
        print("⚠️  没有找到行程规划器使用数据")
        print("   请确认 CF Worker 已部署并有用户使用")
        return
    
    # 分析
    stats = analyze(data)
    
    # 生成报告
    report = generate_report(stats, args.days)
    
    # 保存报告
    report_file = REPORTS_DIR / f"trip_planner_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 报告已生成: {report_file}")
    print(f"\n{'='*60}")
    print(report)
    
    # 导出 CSV
    if args.export_csv:
        export_csv(data, args.export_csv)
        print(f"\n📊 CSV 已导出: {args.export_csv}")

def fetch_cf_data(days=7):
    """从 CF KV 获取数据"""
    if not all([KV_ACCOUNT_ID, KV_API_TOKEN]):
        print("⚠️  CF 环境变量未设置，使用本地模式")
        return load_local_data(days)
    
    import urllib.request
    import urllib.error
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    all_data = []
    
    for i in range(days):
        date_str = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
        key = f"trip-plan:{date_str}"
        
        try:
            url = f"{KV_ENDPOINT}/accounts/{KV_ACCOUNT_ID}/kv/namespaces/{KV_NAMESPACE_ID}/values/{key}"
            req = urllib.request.Request(url, headers={
                'Authorization': f'Bearer {KV_API_TOKEN}',
                'Content-Type': 'application/json'
            })
            
            with urllib.request.urlopen(req) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data.get('details'):
                        all_data.extend(data['details'])
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print(f"⚠️  KV 请求失败 ({date_str}): {e.code}")
        except Exception as e:
            print(f"⚠️  KV 请求异常 ({date_str}): {e}")
    
    return all_data

def load_local_data(days=7):
    """加载本地缓存数据（从 reports/trip-planner/ 目录）"""
    cache_file = REPORTS_DIR / "usage_cache.json"
    
    if not cache_file.exists():
        # 尝试从 reports/llm/ 加载 LLM 调用日志作为参考
        llm_log = PROJECT_ROOT / "reports" / "llm" / "llm_usage_log.json"
        if llm_log.exists():
            print("ℹ️  使用 LLM 调用日志作为参考数据")
            return []
        return []
    
    with open(cache_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze(data):
    """分析使用数据"""
    stats = {
        'total_calls': len(data),
        'date_range': {'start': None, 'end': None},
        'cities': Counter(),
        'durations': Counter(),
        'when': Counter(),
        'interests': Counter(),
        'tokens_used': 0,
        'avg_tokens': 0,
        'daily_counts': defaultdict(int),
    }
    
    for entry in data:
        # 时间
        ts = entry.get('timestamp', '')
        if ts:
            stats['date_range']['start'] = min(stats['date_range']['start'] or ts, ts)
            stats['date_range']['end'] = max(stats['date_range']['end'] or ts, ts)
            date_str = ts.split('T')[0]
            stats['daily_counts'][date_str] += 1
        
        # 城市
        for city in entry.get('cities', []):
            stats['cities'][city] += 1
        
        # 时长
        if entry.get('duration'):
            stats['durations'][entry['duration']] += 1
        
        # 时间计划
        if entry.get('when'):
            stats['when'][entry['when']] += 1
        
        # 兴趣
        for interest in entry.get('interests', []):
            stats['interests'][interest] += 1
        
        # Token
        tokens = entry.get('tokens_used', 0)
        stats['tokens_used'] += tokens
    
    if stats['total_calls'] > 0:
        stats['avg_tokens'] = stats['tokens_used'] // stats['total_calls']
    
    return stats

def generate_report(stats, days=7):
    """生成 Markdown 报告"""
    lines = []
    
    lines.append("# 🧭 AI Trip Planner 使用报告")
    lines.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**分析周期**: 最近 {days} 天")
    lines.append(f"**总调用次数**: {stats['total_calls']}")
    lines.append(f"\n{'='*60}")
    
    # 城市偏好
    lines.append("\n## 🏙️ 城市偏好分布\n")
    if stats['cities']:
        for city, count in stats['cities'].most_common():
            pct = count / stats['total_calls'] * 100
            bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
            lines.append(f"{city:15} {bar} {count:3} ({pct:.1f}%)")
    else:
        lines.append("*暂无数据*")
    
    # 时长分布
    lines.append("\n## ⏱️ 行程时长分布\n")
    if stats['durations']:
        for dur, count in stats['durations'].most_common():
            pct = count / stats['total_calls'] * 100
            lines.append(f"- **{dur}**: {count} 次 ({pct:.1f}%)")
    else:
        lines.append("*暂无数据*")
    
    # 时间计划
    lines.append("\n## 📅 出行时间计划\n")
    if stats['when']:
        for when, count in stats['when'].most_common():
            pct = count / stats['total_calls'] * 100
            lines.append(f"- **{when}**: {count} 次 ({pct:.1f}%)")
    else:
        lines.append("*暂无数据*")
    
    # 兴趣分布
    lines.append("\n## ❤️ 兴趣分布\n")
    if stats['interests']:
        total_interests = sum(stats['interests'].values())
        for interest, count in stats['interests'].most_common():
            pct = count / total_interests * 100
            lines.append(f"- **{interest}**: {count} 次 ({pct:.1f}%)")
    else:
        lines.append("*暂无数据*")
    
    # Token 用量
    lines.append("\n## 💰 Token 用量\n")
    lines.append(f"- 总 Token: {stats['tokens_used']:,}")
    lines.append(f"- 平均/次: {stats['avg_tokens']:,}")
    
    # 选题建议
    lines.append("\n" + "="*60)
    lines.append("\n## 📝 选题反哺建议\n")
    lines.append("基于用户询问频率，建议优先创作：\n")
    
    top_cities = stats['cities'].most_common(3)
    if top_cities:
        lines.append("### 高需求城市指南")
        for city, count in top_cities:
            lines.append(f"1. **{city}** - {count} 次询问")
    
    # 每日趋势
    lines.append("\n## 📈 每日趋势\n")
    if stats['daily_counts']:
        for date in sorted(stats['daily_counts'].keys()):
            count = stats['daily_counts'][date]
            bar = '📊' * min(count, 20)
            lines.append(f"{date}: {bar} ({count})")
    
    lines.append("\n---")
    lines.append(f"\n*报告由 Trip Planner Analytics 自动生成*")
    
    return '\n'.join(lines)

def export_csv(data, output_path):
    """导出 CSV"""
    import csv
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'cities', 'duration', 'when', 'interests', 'tokens_used'])
        
        for entry in data:
            writer.writerow([
                entry.get('timestamp', ''),
                ', '.join(entry.get('cities', [])),
                entry.get('duration', ''),
                entry.get('when', ''),
                ', '.join(entry.get('interests', [])),
                entry.get('tokens_used', 0)
            ])

# ============ 入口 ============

if __name__ == '__main__':
    main()
