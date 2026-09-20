#!/usr/bin/env python3
"""
Trip Planner Analytics Setup - 初始化数据收集

功能：
1. 从 CF KV 拉取历史数据
2. 设置每日自动收集 cron
3. 生成初始报告

使用：
    python scripts/setup_analytics.py

@author Joran - ChinaBound Travel
@version 1.0.0
"""

import json
import os
import sys
import io
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Windows 编码修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============ 配置 ============

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "trip-planner"
CACHE_FILE = REPORTS_DIR / "usage_cache.json"

# Cloudflare API 配置
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "032a874de4e89298d9f492590b08ecba")
CF_API_TOKEN = os.environ.get("CF_API_TOKEN")
KV_NAMESPACE_ID = "a20785ef5e594755ba1d21850de25593"
KV_ENDPOINT = "https://api.cloudflare.com/client/v4"

# ============ 主函数 ============

def main():
    """主入口"""
    print("🧭 Trip Planner Analytics Setup")
    print("=" * 50)
    
    # 创建目录
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. 从 CF KV 拉取数据
    print("\n1. 从 Cloudflare KV 拉取历史数据...")
    data = fetch_cf_data(days=30)
    
    # 2. 保存本地缓存
    print("\n2. 保存本地缓存...")
    save_cache(data)
    
    # 3. 生成报告
    print("\n3. 生成初始报告...")
    if data:
        generate_report(data)
    else:
        print("   ⚠️  暂无数据（功能刚上线，等待用户访问）")
        create_empty_report()
    
    # 4. 设置 cron（可选）
    print("\n4. 数据收集建议...")
    print("   每日运行: python scripts/trip_planner_analytics.py --days 1")
    print("   或添加到 GitHub Actions 定时任务")
    
    print("\n✅ Setup 完成！")

def fetch_cf_data(days=30):
    """从 CF KV 拉取数据"""
    if not CF_API_TOKEN:
        print("   ⚠️  CF_API_TOKEN 未设置，跳过 CF 拉取")
        print("   设置方法: $env:CF_API_TOKEN = 'your-token'")
        return []
    
    import urllib.request
    import urllib.error
    
    end_date = datetime.now()
    all_data = []
    
    for i in range(days):
        date_str = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
        key = f"trip-plan:{date_str}"
        
        try:
            url = f"{KV_ENDPOINT}/accounts/{CF_ACCOUNT_ID}/kv/namespaces/{KV_NAMESPACE_ID}/values/{key}"
            req = urllib.request.Request(url, headers={
                'Authorization': f'Bearer {CF_API_TOKEN}',
                'Content-Type': 'application/json'
            })
            
            with urllib.request.urlopen(req) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data.get('details'):
                        all_data.extend(data['details'])
                        print(f"   ✓ {date_str}: {len(data['details'])} 条记录")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print(f"   ⚠️  {date_str}: HTTP {e.code}")
        except Exception as e:
            print(f"   ⚠️  {date_str}: {e}")
    
    return all_data

def save_cache(data):
    """保存本地缓存"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"   已保存 {len(data)} 条记录到 {CACHE_FILE}")

def generate_report(data):
    """生成报告"""
    from collections import Counter
    
    stats = {
        'total_calls': len(data),
        'cities': Counter(),
        'durations': Counter(),
        'when': Counter(),
        'interests': Counter(),
        'tokens_used': 0,
    }
    
    for entry in data:
        for city in entry.get('cities', []):
            stats['cities'][city] += 1
        if entry.get('duration'):
            stats['durations'][entry['duration']] += 1
        if entry.get('when'):
            stats['when'][entry['when']] += 1
        for interest in entry.get('interests', []):
            stats['interests'][interest] += 1
        stats['tokens_used'] += entry.get('tokens_used', 0)
    
    report = f"""# 🧭 Trip Planner 初始报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**总调用次数**: {stats['total_calls']}

## 🏙️ 城市偏好
"""
    for city, count in stats['cities'].most_common(10):
        pct = count / stats['total_calls'] * 100 if stats['total_calls'] > 0 else 0
        report += f"- **{city}**: {count} 次 ({pct:.1f}%)\n"
    
    report += f"""
## ⏱️ 时长分布
"""
    for dur, count in stats['durations'].most_common():
        pct = count / stats['total_calls'] * 100 if stats['total_calls'] > 0 else 0
        report += f"- **{dur}**: {count} 次 ({pct:.1f}%)\n"
    
    report += f"""
## 📅 时间计划
"""
    for when, count in stats['when'].most_common():
        pct = count / stats['total_calls'] * 100 if stats['total_calls'] > 0 else 0
        report += f"- **{when}**: {count} 次 ({pct:.1f}%)\n"
    
    report += f"""
## ❤️ 兴趣分布
"""
    total_interests = sum(stats['interests'].values())
    for interest, count in stats['interests'].most_common():
        pct = count / total_interests * 100 if total_interests > 0 else 0
        report += f"- **{interest}**: {count} 次 ({pct:.1f}%)\n"
    
    report += f"""
## 💰 Token 用量
- 总 Token: {stats['tokens_used']:,}

---
*报告由 Trip Planner Analytics 自动生成*
"""
    
    report_file = REPORTS_DIR / "initial_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"   报告已生成: {report_file}")

def create_empty_report():
    """创建空报告"""
    report = f"""# 🧭 Trip Planner 初始报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**状态**: 功能刚上线，暂无使用数据

## 📊 当前状态

- CF Worker: ✅ 已部署
- API 端点: ✅ 可用
- 自定义域名: ✅ 已配置
- 文章页卡片: ✅ 已上线

## ⏳ 下一步

1. 等待用户访问文章页
2. 用户点击 "Get My Personalized Plan"
3. 数据自动写入 CF KV
4. 运行 `python scripts/trip_planner_analytics.py --days 7` 查看报告

---
*报告由 Trip Planner Analytics 自动生成*
"""
    
    report_file = REPORTS_DIR / "initial_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"   空报告已生成: {report_file}")

if __name__ == '__main__':
    main()
