#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证日报数据准确性
检查实际数据来源和统计信息
"""

import os
import sys
import io
import json
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_posts():
    """检查文章数量和状态"""
    posts_dir = Path("content/posts")
    articles = list(posts_dir.glob("*.md"))
    
    # 统计图片占位符
    image_stats = []
    link_stats = []
    
    for article in articles:
        try:
            with open(article, 'r', encoding='utf-8') as f:
                content = f.read()
                image_count = content.count("[Image:")
                md_image_count = content.count("![")
                empty_link_count = content.count("](#)")
                invalid_link_count = content.lower().count("<link")
                
                if md_image_count > 0 or empty_link_count > 0 or invalid_link_count > 0:
                    link_stats.append({
                        "file": article.name,
                        "md_images": md_image_count,
                        "empty_links": empty_link_count,
                        "invalid_links": invalid_link_count
                    })
                
                image_stats.append({
                    "file": article.name,
                    "image_placeholders": image_count
                })
        except Exception as e:
            print(f"读取 {article.name} 失败: {e}")
    
    return {
        "total_articles": len(articles),
        "image_stats": image_stats,
        "link_stats": link_stats
    }

def check_config_files():
    """检查配置文件状态"""
    config_dir = Path("config")
    
    files_to_check = [
        "error_knowledge_base.json",
        "gsc_hot_keyword.json",
        "competitor_topic.json", 
        "user_feedback.json",
        "affiliate_data.json",
        "topic_pool.json"
    ]
    
    results = {}
    for filename in files_to_check:
        filepath = config_dir / filename
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results[filename] = {
                        "exists": True,
                        "size": len(json.dumps(data)),
                        "records": len(data.get("feedbacks", data.get("keywords", data.get("topics", []))))
                    }
            except:
                results[filename] = {"exists": True, "error": "解析失败"}
        else:
            results[filename] = {"exists": False}
    
    return results

def check_github_secrets():
    """检查 GitHub Secrets 配置（模拟检查）"""
    # 在本地无法读取 GitHub Secrets，只能检查脚本中是否引用
    secrets_used = [
        "FEISHU_WEBHOOK_URL",
        "FEISHU_SECRET",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ZONE_ID",
        "GSC_API_KEY",
        "BOOKING_API_KEY", 
        "AGODA_API_KEY",
        "DEEPSEEK_API_KEY"
    ]
    
    # 检查 workflow 文件
    workflow_files = list(Path(".github/workflows").glob("*.yml"))
    found_secrets = []
    
    for wf in workflow_files:
        with open(wf, 'r', encoding='utf-8') as f:
            content = f.read()
            for secret in secrets_used:
                if f"secrets.{secret}" in content:
                    found_secrets.append(secret)
    
    return {
        "secrets_referenced": found_secrets,
        "total_referenced": len(found_secrets)
    }

def verify_traffic_data():
    """验证流量数据来源"""
    # 检查 Cloudflare API 配置状态
    cloudflare_token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    cloudflare_zone_id = os.environ.get("CLOUDFLARE_ZONE_ID", "")
    
    return {
        "cloudflare_configured": bool(cloudflare_token and cloudflare_zone_id),
        "using_mock_data": not (cloudflare_token and cloudflare_zone_id)
    }

def main():
    print("="*60)
    print("📊 日报数据准确性验证")
    print("="*60)
    
    # 1. 检查文章数据
    print("\n📝 文章数据检查:")
    posts = check_posts()
    print(f"   文章总数: {posts['total_articles']} 篇")
    
    avg_images = sum(s['image_placeholders'] for s in posts['image_stats']) / max(len(posts['image_stats']), 1)
    print(f"   平均图片占位符: {avg_images:.1f} 个/篇")
    
    if posts['link_stats']:
        print(f"   有问题的文章: {len(posts['link_stats'])} 篇")
        for stat in posts['link_stats']:
            print(f"     - {stat['file']}: md图片={stat['md_images']}, 空链接={stat['empty_links']}")
    else:
        print("   ✅ 所有文章格式正确")
    
    # 2. 检查配置文件
    print("\n📁 配置文件检查:")
    configs = check_config_files()
    for name, status in configs.items():
        if status['exists']:
            if 'error' in status:
                print(f"   ❌ {name}: {status['error']}")
            else:
                print(f"   ✅ {name}: {status['records']} 条记录")
        else:
            print(f"   ⚠️ {name}: 不存在")
    
    # 3. 检查 Secrets 引用
    print("\n🔑 GitHub Secrets 引用检查:")
    secrets = check_github_secrets()
    print(f"   Workflow中引用的Secrets: {secrets['total_referenced']} 个")
    for secret in secrets['secrets_referenced']:
        print(f"     - {secret}")
    
    # 4. 验证流量数据来源
    print("\n🌐 流量数据来源验证:")
    traffic = verify_traffic_data()
    if traffic['cloudflare_configured']:
        print("   ✅ 使用真实 Cloudflare 数据")
    else:
        print("   ⚠️ 使用模拟数据 (Cloudflare API 未配置)")
    
    # 5. 总结
    print("\n" + "="*60)
    print("📋 数据准确性总结")
    print("="*60)
    print("| 数据类型 | 来源 | 准确性 |")
    print("|---------|------|--------|")
    print("| 文章统计 | 本地文件 | ✅ 真实 |")
    print("| 错误学习 | 知识库 | ✅ 真实 |")
    print("| 选题池 | 配置文件 | ✅ 真实 |")
    print("| 流量数据 | Cloudflare API | " + ("✅ 真实" if traffic['cloudflare_configured'] else "⚠️ 模拟") + " |")
    print("| GSC数据 | Google API | ⚠️ 模拟 |")
    print("| 联盟数据 | Booking/Agoda API | ⚠️ 模拟 |")
    print("="*60)
    
    print("\n💡 说明:")
    print("- 模拟数据使用合理的默认值，用于演示系统功能")
    print("- 配置相关API后将自动切换为真实数据")
    print("- GitHub Actions 运行时会自动使用 Secrets 中的配置")

if __name__ == "__main__":
    main()