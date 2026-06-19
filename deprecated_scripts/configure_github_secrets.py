#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Secrets Configuration Helper
This script helps configure GitHub Secrets for the ChinaBound Travel project
"""

import os
import json

def print_configuration_guide():
    """打印配置指南"""
    guide = """
╔═══════════════════════════════════════════════════════════════╗
║         GitHub Secrets 配置指南                               ║
╚═══════════════════════════════════════════════════════════════╝

┌───────────────────────────────────────────────────────────────┐
│ 1. 配置 Vercel Token (CHINABOUND)                             │
├───────────────────────────────────────────────────────────────┤
│ 如何获取:                                                     │
│  1. 访问 https://vercel.com/account/tokens                    │
│  2. 点击 "Create Token"                                       │
│  3. 输入 Token 名称（如 "chinabound-deploy"）                 │
│  4. 点击 "Create"                                             │
│  5. 复制生成的 Token                                          │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ 2. 配置 Cloudflare API Token                                  │
├───────────────────────────────────────────────────────────────┤
│ 如何获取:                                                     │
│  1. 访问 https://dash.cloudflare.com/profile/api-tokens       │
│  2. 点击 "Create Token"                                       │
│  3. 选择 "Edit Cloudflare Pages" 模板                         │
│  4. 点击 "Continue to summary"                                │
│  5. 点击 "Create Token"                                       │
│  6. 复制生成的 Token                                          │
│                                                               │
│ 需要配置的 Secrets:                                           │
│  - CLOUDFLARE_API_TOKEN                                       │
│  - CLOUDFLARE_ACCOUNT_ID                                      │
│                                                               │
│ 如何获取 Account ID:                                          │
│  1. 访问 https://dash.cloudflare.com/                         │
│  2. 在页面右下角可以看到 Account ID                           │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ 3. 配置飞书 Webhook (FEISHU_WEBHOOK_URL)                      │
├───────────────────────────────────────────────────────────────┤
│ 如何获取:                                                     │
│  1. 打开飞书群聊                                              │
│  2. 点击群设置 -> 群机器人 -> 添加机器人 -> 自定义机器人      │
│  3. 输入机器人名称，上传头像（可选）                           │
│  4. 点击 "创建"                                               │
│  5. 复制 "Webhook 地址"                                       │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ 4. 在 GitHub 中配置 Secrets                                   │
├───────────────────────────────────────────────────────────────┤
│ 操作步骤:                                                     │
│  1. 访问你的仓库: https://github.com/fys2388/chinaboundtravel │
│  2. 点击 "Settings"                                          │
│  3. 在左侧菜单点击 "Secrets and variables" -> "Actions"       │
│  4. 点击 "New repository secret"                              │
│  5. 依次添加以下 Secrets:                                     │
│     - CHINABOUND (Vercel Token)                               │
│     - CLOUDFLARE_API_TOKEN                                    │
│     - CLOUDFLARE_ACCOUNT_ID                                   │
│     - FEISHU_WEBHOOK_URL (可选，用于飞书通知)                  │
└───────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════╗
║                    报告推送逻辑说明                            ║
╚═══════════════════════════════════════════════════════════════╝

每日巡检:
├── 触发时间: 每天 09:30 (北京时间)
├── 执行内容: 网站可访问性、SSL证书、Sitemap、重定向、乱码、内链检查
├── 报告类型: 日报
└── 推送方式: 飞书通知

周报:
├── 触发时间: 每周日 20:00 (北京时间)
├── 执行内容: 同每日巡检
├── 报告类型: 周报
└── 推送方式: 飞书通知

月报:
├── 触发时间: 每月1号 09:30 (北京时间)
├── 执行内容: 同每日巡检
├── 报告类型: 月报
└── 推送方式: 飞书通知

注意: 如果当天既是周日又是每月1号，优先生成月报。
    """
    print(guide)

def main():
    print_configuration_guide()
    
    # 检查本地配置文件
    if os.path.exists('.env'):
        print("\n检测到本地 .env 文件，内容如下:")
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)

if __name__ == "__main__":
    main()