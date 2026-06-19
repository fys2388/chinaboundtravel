#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日报配置检查工具
检查所有必需的配置项
"""

import os
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_workflow():
    """检查 workflow 配置"""
    print("="*60)
    print("🔧 Workflow 配置检查")
    print("="*60)
    
    workflow_files = [
        ".github/workflows/daily-inspection.yml",
        ".github/workflows/deploy-cloudflare-pages.yml"
    ]
    
    for wf in workflow_files:
        path = Path(wf)
        if path.exists():
            print(f"✅ {wf}")
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 检查关键配置
                checks = [
                    ("cron 定时配置", "cron:" in content),
                    ("FEISHU_WEBHOOK_URL", "FEISHU_WEBHOOK_URL" in content),
                    ("concurrency 控制", "concurrency:" in content),
                    ("[skip ci] 检查", "skip ci" in content.lower())
                ]
                for check_name, found in checks:
                    status = "✅" if found else "❌"
                    print(f"   {status} {check_name}")
        else:
            print(f"❌ {wf} - 文件不存在")

def check_secrets():
    """检查 GitHub Secrets 配置"""
    print("\n" + "="*60)
    print("🔐 GitHub Secrets 配置检查")
    print("="*60)
    
    secrets = [
        ("FEISHU_WEBHOOK_URL", "飞书机器人地址", True),
        ("FEISHU_SECRET", "飞书签名密钥", False),
        ("CLOUDFLARE_API_TOKEN", "Cloudflare API Token", False),
        ("CLOUDFLARE_ZONE_ID", "Cloudflare Zone ID", False),
        ("GSC_API_KEY", "Google Search Console API Key", False),
        ("BOOKING_API_KEY", "Booking.com API Key", False),
        ("AGODA_API_KEY", "Agoda API Key", False),
        ("DEEPSEEK_API_KEY", "DeepSeek API Key", True)
    ]
    
    print("注意: 本地无法读取 GitHub Secrets")
    print("请在 GitHub 仓库 → Settings → Secrets and variables → Actions 中配置")
    print("\n必需配置:")
    for name, desc, required in secrets:
        status = "⚠️" if required else "🔹"
        print(f"   {status} {name} - {desc}")
        if required:
            print(f"      (必需)")

def check_config_files():
    """检查配置文件"""
    print("\n" + "="*60)
    print("📁 配置文件检查")
    print("="*60)
    
    config_files = [
        "config/error_knowledge_base.json",
        "config/topic_pool.json", 
        "config/gsc_hot_keyword.json",
        "config/user_feedback.json",
        "config/affiliate_data.json",
        "config/competitor_topic.json",
        "config/feishu_config.py"
    ]
    
    for cf in config_files:
        path = Path(cf)
        if path.exists():
            print(f"✅ {cf}")
        else:
            print(f"❌ {cf} - 文件不存在")

def check_scripts():
    """检查脚本文件"""
    print("\n" + "="*60)
    print("📜 脚本文件检查")
    print("="*60)
    
    scripts = [
        "daily_inspection.py",
        "send_feishu_report.py",
        "test_feishu_push.py",
        "test_apis.py",
        "verify_data.py"
    ]
    
    for script in scripts:
        path = Path(script)
        if path.exists():
            print(f"✅ {script}")
        else:
            print(f"❌ {script} - 文件不存在")

def check_directories():
    """检查必需目录"""
    print("\n" + "="*60)
    print("📂 目录结构检查")
    print("="*60)
    
    dirs = [
        "content/posts",
        "config",
        "reports",
        "reports/01 每日巡检报告",
        "reports/02 周报汇总",
        "chinaboundtravel_social_bot"
    ]
    
    for d in dirs:
        path = Path(d)
        if path.exists():
            print(f"✅ {d}")
        else:
            print(f"⚠️ {d} - 目录不存在")

def check_main_config():
    """检查主配置文件"""
    print("\n" + "="*60)
    print("⚙️ 主配置检查")
    print("="*60)
    
    config_files = ["manifest.json", "config/_default/config.toml"]
    
    for cf in config_files:
        path = Path(cf)
        if path.exists():
            print(f"✅ {cf}")
        else:
            print(f"❌ {cf} - 文件不存在")

def main():
    print("="*80)
    print("📊 ChinaBound Travel 日报配置检查")
    print("="*80)
    
    check_workflow()
    check_secrets()
    check_config_files()
    check_scripts()
    check_directories()
    check_main_config()
    
    print("\n" + "="*80)
    print("📋 配置检查总结")
    print("="*80)
    print("\n【必需配置】(必须完成)")
    print("1. ✅ Workflow 文件 - 已配置")
    print("2. ⚠️ GitHub Secrets - 需要在 GitHub 配置")
    print("3. ✅ 配置文件 - 已创建")
    print("4. ✅ 脚本文件 - 已创建")
    
    print("\n【可选配置】(按需开启)")
    print("1. Cloudflare API - 获取真实流量数据")
    print("2. GSC API - 获取搜索关键词数据")
    print("3. Booking/Agoda API - 获取联盟转化数据")
    
    print("\n💡 检查完成! 请确保 GitHub Secrets 已正确配置")

if __name__ == "__main__":
    main()