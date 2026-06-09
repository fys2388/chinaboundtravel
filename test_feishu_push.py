#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试飞书推送 - 支持通过参数传入配置
"""

import os
import sys
import io
import hashlib
import hmac
import base64
import time
import requests
from datetime import datetime
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def generate_signature(secret, timestamp):
    """生成飞书签名"""
    string_to_sign = f"{timestamp}\n{secret}"
    signature = hmac.new(
        secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode('utf-8')

def generate_daily_report():
    """生成每日巡检报告"""
    report = f"""📊 **ChinaBound Travel 每日巡检报告** ({datetime.now().strftime('%Y-%m-%d')})

✅ **整体状态**: 全部正常

📋 **问题明细**:
- 编码问题: 0 个文件
- 内容合规: 0 个问题
- 链接检查: 0 个问题
- 配图格式: 0 个待优化

🌐 **站点状态**: 🟢 在线

📈 **流量数据**:
- 独立访客: 1,234 (昨日)
- 页面浏览: 3,567 (昨日)
- 热门页面: /posts/budget-planning-china/

🔍 **市场对标**:
- GSC热搜关键词: 10 条
- 竞品热点趋势: 8 个方向
- 联盟转化: 77 单 (本周)
- 用户反馈: 15 条 (本周)
- 新增选题: 5 个

🧠 **Joran学习进度**:
- 已掌握: 8 种错误模式
- 待学习: 2 种
- 学习进度: 80%

📚 **Joran学习笔记**

近期发现需要避免的错误模式：

🔹 **配图格式**: 配图数量不足
   - 出现次数: 3 次
   - 修复建议: 每篇文章至少添加2个图片占位符 [Image:xxx]

🔹 **链接问题**: 空链接未填充
   - 出现次数: 2 次
   - 修复建议: 填充有效的站内链接或删除空链接

💡 请将这些错误模式添加到内容生成规则中，避免再次生成相同错误。

---
*AI运维专员 | {datetime.now().strftime('%Y-%m-%d %H:%M')} 自动推送*"""

    return report

def send_to_feishu(webhook_url, secret, message):
    """发送消息到飞书"""
    if not webhook_url:
        print("❌ webhook_url 未设置")
        return False

    try:
        timestamp = str(int(time.time()))
        signature = generate_signature(secret, timestamp) if secret else ""

        payload = {
            "timestamp": timestamp,
            "sign": signature,
            "msg_type": "text",
            "content": {
                "text": message
            }
        }

        print(f"📤 正在推送至飞书...")
        response = requests.post(webhook_url, json=payload, timeout=10)

        if response.status_code == 200:
            print("✅ 飞书日报推送成功!")
            return True
        else:
            print(f"❌ 推送失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 推送异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试飞书日报推送")
    parser.add_argument("--webhook", type=str, help="飞书 Webhook URL")
    parser.add_argument("--secret", type=str, help="飞书 Secret (可选)")
    
    args = parser.parse_args()

    # 获取配置
    webhook_url = args.webhook or os.environ.get("FEISHU_WEBHOOK_URL", "")
    secret = args.secret or os.environ.get("FEISHU_SECRET", "")

    print("="*60)
    print("ChinaBound Travel 飞书日报推送测试")
    print("="*60)

    if not webhook_url:
        print("❌ 请提供飞书 Webhook URL")
        print("")
        print("使用方法:")
        print("  python test_feishu_push.py --webhook <飞书webhook地址>")
        print("")
        print("或设置环境变量:")
        print("  set FEISHU_WEBHOOK_URL=<飞书webhook地址>")
        print("  python test_feishu_push.py")
        sys.exit(1)

    # 生成报告
    report = generate_daily_report()

    # 发送飞书
    send_to_feishu(webhook_url, secret, report)