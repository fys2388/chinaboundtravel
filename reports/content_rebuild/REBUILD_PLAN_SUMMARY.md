# P1-CONTENT-TRUST-REBUILD-PLAN-01 重构计划（阶段1 只读审计）

生成时间: 2026-08-24 18:28:21

## 概述

- 审计问题总数: **1128**
- 涉及文章数: **58**
- 预计修改问题数: **1090**（voice+hallucination+language+fact 队列）

> 本阶段为**只读**：未修改任何 content 文件。
> 保持 **URL / slug / canonical / content_id / SEO metadata** 不变。

## 修复队列

| 队列 | 问题数 | 自动修复 | 人工审核 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| VOICE_FIX_PREVIEW | 338 | 338 | 0 | 第一人称→编辑部口吻 |
| AI_HALLUCINATION | 359 | 326 | 33 | 绝对化/无来源数据 |
| LANGUAGE_FIX | 14 | 14 | 0 | 中文残留 |
| FACT_CHECK_QUEUE | 379 | 0 | 379 | 价格/时间/政策 人工核对 |

## 修改数量预测

- **预计总修改问题数**: 1090
- **可自动修复**: 678（62.2%）
- **需人工审核**: 412（37.8%）

## 高风险文章 TOP20

| # | content_id | 文章 | 风险分 |
| :--- | :--- | :--- | :--- |
| 1 | cbt-34777b6c17c1 | Zhangjiajie Guide: Avatar Mountains & Itinerary | 42 |
| 2 | cbt-23c31fe5b281 | Yunnan Travel Guide: Rice Terraces & Ancient Towns | 42 |
| 3 | cbt-1005a037234b | China Food Guide for European Travelers | 42 |
| 4 | cbt-9e2f5ffa1b6d | Where to Stay in China: Hotels & Budget Options | 41 |
| 5 | cbt-cfd5d7b39f09 | Chinese Language Survival Phrases Guide 2026 | 41 |
| 6 | cbt-244822dc113b | China | 41 |
| 7 | cbt-a349eee78670 | Internet in China: eSIM vs SIM vs VPN (2026) — For | 41 |
| 8 | cbt-e464169c4991 | Chinese Food Delivery: Meituan & Ele.me Guide | 40 |
| 9 | cbt-558f85f45e9a | Great Wall of China: History Beyond the Tourist Tr | 40 |
| 10 | cbt-663ab3f3b0fa | Shanghai Beyond the Bund: Hidden Neighborhoods | 40 |
| 11 | cbt-255af4ed003a | How to Set Up & Use WeChat Pay Step by Step (2026  | 40 |
| 12 | cbt-baa2f6fba2f0 | Where to Stay in China: Complete 2026 Guide | 40 |
| 13 | cbt-d701fb08eb7b | Best Travel Insurance for China 2026 | 40 |
| 14 | cbt-dfe3904705ea | China Travel Safety 2026: Guide for Travelers | 39 |
| 15 | cbt-bc3e1afe5dc0 | Shanghai Vs Beijing: Which Chinese City Should You | 39 |
| 16 | cbt-302467d853db | Shanghai 48-Hour Guide: Bund & French Concession | 38 |
| 17 | cbt-80ac63165adb | China Travel Guide: August 2026 Updates & Visa Rul | 38 |
| 18 | cbt-80f6c218ad94 | Western Sichuan Overland Camping Route: 7 Days | 38 |
| 19 | cbt-d7747b73c978 | Xi | 36 |
| 20 | cbt-bf4ec5e57a07 | Guilin & Yangshuo: Complete 2026 Travel Guide | 36 |

## 每篇文章修改预估（前10）

| 文章 | voice | hallucination | language | fact | 合计 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Zhangjiajie Guide: Avatar Mountains & It | 8 | 8 | 1 | 8 | 25 |
| Yunnan Travel Guide: Rice Terraces & Anc | 8 | 8 | 1 | 8 | 25 |
| China Food Guide for European Travelers | 8 | 8 | 1 | 8 | 25 |
| Chinese Food Delivery: Meituan & Ele.me  | 8 | 8 | 0 | 8 | 24 |
| Great Wall of China: History Beyond the  | 8 | 8 | 0 | 8 | 24 |
| Shanghai Beyond the Bund: Hidden Neighbo | 8 | 8 | 0 | 8 | 24 |
| How to Set Up & Use WeChat Pay Step by S | 8 | 8 | 0 | 8 | 24 |
| Where to Stay in China: Hotels & Budget  | 8 | 8 | 0 | 8 | 24 |
| Where to Stay in China: Complete 2026 Gu | 8 | 8 | 0 | 8 | 24 |
| Chinese Language Survival Phrases Guide  | 8 | 8 | 1 | 7 | 24 |