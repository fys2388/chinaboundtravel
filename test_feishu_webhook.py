#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书 Webhook 测试脚本
"""

import requests
import json
import sys

# 飞书 Webhook URL
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/***REMOVED***"

def send_test_message():
    """发送测试消息到飞书"""
    print("=" * 60)
    print("飞书 Webhook 测试")
    print("=" * 60)
    
    # 测试消息
    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🎉 ChinaBound Travel 自动化测试"
                },
                "template": "green"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**✅ 连接成功！**\n\n这是来自 **ChinaBound Travel** 自动化系统的测试消息。\n\n📊 **自动化配置状态：**\n- ✅ GitHub Secrets 已配置\n- ✅ 飞书 Webhook 已连接\n- ✅ 每日巡检已就绪\n- ✅ 报告推送已开启"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "测试时间: "
                        },
                        {
                            "tag": "plain_text",
                            "content": "2026-06-01"
                        }
                    ]
                }
            ]
        }
    }
    
    print(f"\n📤 正在发送测试消息到飞书...")
    print(f"   Webhook: {WEBHOOK_URL[:50]}...")
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(message),
            timeout=30
        )
        
        result = response.json()
        print(f"\n📥 响应状态码: {response.status_code}")
        print(f"📋 响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200 and result.get("StatusCode") == 0:
            print("\n" + "=" * 60)
            print("🎉 测试成功！飞书连接已接通！")
            print("=" * 60)
            print("\n📱 请检查您的飞书群，应该收到了一条绿色卡片消息。")
            return True
        else:
            print("\n" + "=" * 60)
            print("⚠️ 测试失败！")
            print("=" * 60)
            print(f"错误码: {result.get('StatusCode', 'N/A')}")
            print(f"错误信息: {result.get('msg', 'Unknown error')}")
            return False
            
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 测试失败: {str(e)}")
        print("=" * 60)
        return False

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    send_test_message()
