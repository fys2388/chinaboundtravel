#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送阶段一测试报告到飞书
"""

import requests
import json
import sys

WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/***REMOVED***"

def send_report():
    """发送阶段一测试报告"""
    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📊 阶段一：基础站点架构 & 环境预测试报告"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**测试时间：** 2026-06-01\n\n**测试结果总结：**"
                    }
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": "✅ **通过**: 2 项"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": "⚠️ **需修复**: 1 项"
                            }
                        }
                    ]
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**📁 1.1 目录结构完整性：** ✅ 通过\n- `posts/` - 免费公开内容\n- `static-package/` - 一次性买断产品\n- `member-month/` - 月度会员专属\n- `member-year/` - 年度会员专属"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**🔗 1.2 域名重定向 & HTTPS：** ⚠️ 部分通过\n- ✅ `https://www.chinaboundtravel.com` - 正常访问\n- ✅ `http://www.chinaboundtravel.com` - 正确重定向 HTTPS\n- ⚠️ `https://chinaboundtravel.com` - 未正确重定向到 www"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**🔒 1.3 会员专区 noindex：** ✅ 通过\n- 所有付费专区已配置 `noindex, nofollow`，防止搜索引擎收录"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**📄 1.4 静态文件访问：** ⏳ 待部署后测试"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**⚠️ 待修复问题：**\n1. **域名重定向** - 裸域 `https://chinaboundtravel.com` 需要配置重定向到 www 版本"
                    }
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "详细报告已保存到 phase1_test_report.md"
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(message),
            timeout=30
        )
        result = response.json()
        if response.status_code == 200 and result.get("StatusCode") == 0:
            print("✅ 报告已发送到飞书")
        else:
            print(f"❌ 发送失败: {result}")
    except Exception as e:
        print(f"❌ 发送异常: {e}")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    send_report()
