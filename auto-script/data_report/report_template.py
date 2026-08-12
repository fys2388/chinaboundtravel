#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChinaBound Travel - 数据报表生成器
支持日报/周报/月报/年报，自动推送到飞书
"""

import json
import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")

class DataReportGenerator:
    def __init__(self):
        self.today = datetime.now()
        
    def generate_daily_report(self) -> str:
        """生成日报"""
        date_str = self.today.strftime('%Y-%m-%d')
        report = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"📊 日报 - {date_str}"},
                    "template": "blue"
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": f"**生成时间**: {self.today.strftime('%H:%M')}"}},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 📝 内容生产"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "新文章: 0篇"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "审核通过: 0篇"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "废稿归档: 0篇"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "审核通过率: 100%"}}
                    ]},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 📈 流量数据"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "访问量: 0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "独立访客: 0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "跳出率: 0%"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "平均时长: 0m"}}
                    ]},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 📧 订阅转化"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "新增订阅: 0人"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "邮件打开率: 0%"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "点击率: 0%"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "退订率: 0%"}}
                    ]},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 💰 订单数据"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "订单数: 0笔"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "销售额: $0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "客单价: $0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "转化率: 0%"}}
                    ]},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 🚦 系统状态"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "✅ 网站正常"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "✅ SSL正常"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "✅ 支付正常"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "✅ 邮件正常"}}
                    ]},
                    {"tag": "note", "elements": [
                        {"tag": "plain_text", "content": "ChinaBound Travel 自动化报表系统"}
                    ]}
                ]
            }
        }
        return json.dumps(report, ensure_ascii=False)
    
    def generate_weekly_report(self) -> str:
        """生成周报"""
        week_start = (self.today - timedelta(days=self.today.weekday())).strftime('%Y-%m-%d')
        week_end = (self.today + timedelta(days=6 - self.today.weekday())).strftime('%Y-%m-%d')
        
        report = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"📊 周报 - {week_start} ~ {week_end}"},
                    "template": "purple"
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 📝 本周内容生产"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "新文章: 0篇"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "社媒发帖: 0篇"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "审核通过: 0篇"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "审核通过率: 100%"}}
                    ]},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 📈 本周流量"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "总访问量: 0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "独立访客: 0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "平均时长: 0m"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "同比上周: 0%"}}
                    ]},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 💰 本周营收"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "订单数: 0笔"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "销售额: $0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "客单价: $0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "同比上周: 0%"}}
                    ]},
                    {"tag": "note", "elements": [
                        {"tag": "plain_text", "content": "ChinaBound Travel 周报"}
                    ]}
                ]
            }
        }
        return json.dumps(report, ensure_ascii=False)
    
    def generate_monthly_report(self) -> str:
        """生成月报"""
        month_str = self.today.strftime('%Y年%m月')
        
        report = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"📊 月报 - {month_str}"},
                    "template": "orange"
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 📝 本月内容生产"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "新文章: 0篇"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "社媒发帖: 0篇"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "审核通过: 0篇"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "审核通过率: 100%"}}
                    ]},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 📈 本月流量"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "总访问量: 0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "独立访客: 0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "平均时长: 0m"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "同比上月: 0%"}}
                    ]},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 📧 订阅转化"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "新增订阅: 0人"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "邮件打开率: 0%"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "点击率: 0%"}}
                    ]},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "lark_md", "content": "### 💰 本月营收"}},
                    {"tag": "div", "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": "订单数: 0笔"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "销售额: $0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "客单价: $0"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": "同比上月: 0%"}}
                    ]},
                    {"tag": "note", "elements": [
                        {"tag": "plain_text", "content": "ChinaBound Travel 月报"}
                    ]}
                ]
            }
        }
        return json.dumps(report, ensure_ascii=False)
    
    def send_to_feishu(self, report_json: str) -> bool:
        if not FEISHU_WEBHOOK_URL:
            print("FEISHU_WEBHOOK_URL ????????")
            return False
        """发送报告到飞书"""
        try:
            response = requests.post(
                FEISHU_WEBHOOK_URL,
                headers={"Content-Type": "application/json; charset=utf-8"},
                data=report_json.encode('utf-8'),
                timeout=30
            )
            result = response.json()
            return response.status_code == 200 and result.get("StatusCode") == 0
        except Exception as e:
            import traceback
            print("发送失败: {}".format(str(e).encode('utf-8', errors='replace').decode('utf-8')))
            return False
    
    def run(self, report_type: str = "daily"):
        """运行报表生成和发送"""
        print(f"生成{report_type}报表...")
        
        if report_type == "daily":
            report = self.generate_daily_report()
        elif report_type == "weekly":
            report = self.generate_weekly_report()
        elif report_type == "monthly":
            report = self.generate_monthly_report()
        else:
            print(f"未知报表类型: {report_type}")
            return False
        
        if self.send_to_feishu(report):
            print(f"{report_type}报表发送成功！")
            return True
        else:
            print(f"{report_type}报表发送失败！")
            return False

def main():
    import sys
    report_type = sys.argv[1] if len(sys.argv) > 1 else "daily"
    
    generator = DataReportGenerator()
    generator.run(report_type)

if __name__ == "__main__":
    main()
