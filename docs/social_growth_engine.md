# ChinaBound 社媒增长引擎使用说明

> 项目路径：`e:\AI\dulizhan\travel-blog`
> 目标：把 60 篇存量文章转化为可持续发布的社媒内容（**内容资产库 → AI 拆解生成 → 双账户分发 → 数据回流**），不依赖新文章也能每日更新。

---

## 一、架构总览

```
content/social/inventory.json   ← 内容资产库（JSON 底层存储，100+ 条素材）
        │
        ▼
scripts/social_content_agent.py ← 核心 Agent（生成 / 筛选 / 排期 / 分发 / 回流）
        │
        ├─► 双 Buffer Worker 分发（Account-A 非Pin / Account-B Pin）
        │       BUFFER_WORKER_URL          → IG / X / FB
        │       NEW_BUFFER_WORKER_URL      → Pinterest
        │
        └─► scripts/social_reports.py  → 日报社媒板块 / 周报社媒增长复盘
```

| 模块 | 文件 | 职责 |
|------|------|------|
| 资产库 | `content/social/inventory.json` | 素材唯一存储，含 caption / image_prompt / UTM / 状态 / metrics |
| 核心 Agent | `scripts/social_content_agent.py` | 批量生成、筛选、排期、发布、数据回流 |
| 报表 | `scripts/social_reports.py` | 渲染飞书卡片社媒板块（日报/周报） |
| 测试 | `tests/test_social_content_agent.py` | 引擎行为测试（26 项） |

---

## 二、快速开始

### 1. 构建首批素材资产库（100 条）

```bash
cd e:\AI\dulizhan\travel-blog
python scripts/social_content_agent.py build-inventory --top-n 20
```

- 自动从 60 篇存量文章中选出 **Top-20 高价值文章**（按 GA4 历史流量 + front matter 信号）。
- 每篇生成 **5 条**（覆盖 5 种 type：`knowledge / tip / story / visual / conversion`），共 **100 条**。
- 4 个平台整体均衡（各 25 条）：`ig / pinterest / x / fb`。
- 全程 **2.0 Editorial Voice**，禁第一人称个人体验表述；自动调用品牌审计（`brand_identity_audit.scan_text`），不合格自动重写，**最多 3 轮**。
- 幂等：已存在的签名（同篇同平台同类型）不重复生成，`--force` 强制重建。

### 2. 列出 / 筛选素材

```bash
python scripts/social_content_agent.py list --platform ig
python scripts/social_content_agent.py list --type visual --status 待审核
python scripts/social_content_agent.py list --article china-high-speed-rail-how-to-book-tickets
```

### 3. 生成排期

```bash
python scripts/social_content_agent.py plan --date 2026-08-21
```

排期策略：
- **每日 3 条**，美东黄金时段 `08:00 / 18:00 / 22:00`（脚本按 EDT -4 换算为 UTC）。
- **80% 价值型**（knowledge/tip/story）+ **20% 转化型**（conversion）。
- **同篇 7 天内不重复**发布。

### 4. 发布

```bash
# 自动模式：直接发布排期当天批次
python scripts/social_content_agent.py publish --auto --date 2026-08-21

# 半自动模式：列出待发素材，人工确认后逐个推送
python scripts/social_content_agent.py publish            # 交互确认前 3 条待审核
python scripts/social_content_agent.py publish --confirm --item-ids soc-000001,soc-000002
```

发布成功自动回写资产库：`status="已发布"`、`publish_date=今天`。

> 默认 `publish` 为 **dry-run**（不真实发请求）。加 `--auto` 或 `--confirm` 才真实调用 Buffer Worker。

### 5. 数据回流

```bash
python scripts/social_content_agent.py backfill-metrics --file path/to/metrics.json
```

`metrics.json` 格式（item_id 对应资产库 `id`）：

```json
{
  "items": [
    {"item_id": "soc-000001", "impressions": 1200, "clicks": 45, "engagements": 18, "uv": 30}
  ]
}
```

### 6. 日报 / 周报社媒板块

```bash
# 日报：昨日发布数、各平台曝光/点击/引流UV
python scripts/social_reports.py daily --print-block

# 周报：总量、分平台、Top5/Bottom5、类型对比、下周建议
python scripts/social_reports.py weekly --print-block
```

输出 JSON 存到 `reports/social/`，`--print-block` 打印飞书卡片 block。

---

## 三、双 Buffer Worker 对接

复用 `scripts/social_backfill.py` 的端点配置：

| 平台 | Worker URL 环境变量 | 默认端点 |
|------|---------------------|---------|
| IG / X / FB | `BUFFER_WORKER_URL` | `https://buffer-worker.chinaboundtravel.com/publish` |
| Pinterest | `NEW_BUFFER_WORKER_URL` | 同 Account-A 端点（Worker 内部按账户分流） |

发布 payload 携带可追溯字段：`source_workflow="social_content_agent"`、`content_variant="{platform}_{type}"`，与现有 `social_publisher` / `content_rotator` 保持一致。

---

## 四、预留接口（可后续接入）

### LLM 文案增强
`scripts/social_content_agent.py` 的 `llm_enhance()` 是预留接口：
- 设 `SOCIAL_LLM_ENABLED=1` + `DEEPSEEK_API_KEY`（或 `DOUBAO_ARK_API_KEY`）即调用；
- 未启用 / 无 key / 调用失败 → **确定性降级到模板生成**（保证离线可复现、测试全绿）。

### 图片生成
`generate_image()` 是预留接口，读取 `IMAGE_GEN_ENABLED` 开关；当前返回空串（表示未生成）。接入 pollinations / Stable Diffusion 后，把 `image_prompt` 渲染成图片并回填 `image_url` 供发布填充 `cover`。

---

## 五、数据回流与复盘

- **metrics 沉淀**：每次发布/回流把曝光、点击、互动、引流 UV 写回资产库 `metrics` 字段。
- **日报板块**：昨日发布数 + 各平台曝光/点击/UV。
- **周报板块**：本周总量、分平台数据、**高表现 Top5 / 低表现 Bottom5**、**内容类型效果对比**、下周优化建议。
- **持续迭代**：基于周报表现自动调整生成策略（复用高表现 type+platform 组合）。

---

## 六、测试

```bash
cd e:\AI\dulizhan\travel-blog
python -m pytest tests -q
```

引擎专项测试：`python -m pytest tests/test_social_content_agent.py -q`
（覆盖资产库结构、生成合规、平台长度、排期 80/20 与 7 天去重、双 Worker 分发 mock、数据回流、日报/周报汇总。）

---

## 七、错误降级与飞书通知

- 复用 `scripts/logger.py`（日志写到 `logs/social_content_agent.log`）。
- 复用 `scripts/error_handler.py`（错误分类 / 知识库沉淀）。
- 飞书通知走 `FEISHU_WEBHOOK_URL`，未配置或失败时静默跳过（不影响主流程）。
- LLM / 图片 / Worker 任一步失败均降级或记录，不中断资产库与排期。

---

## 八、文件清单

| 文件 | 说明 |
|------|------|
| `content/social/inventory.json` | 内容资产库（100 条素材） |
| `scripts/social_content_agent.py` | 核心 Agent（生成/筛选/排期/分发/回流） |
| `scripts/social_reports.py` | 日报/周报社媒板块渲染 |
| `tests/test_social_content_agent.py` | 引擎行为测试 |
| `docs/social_growth_engine.md` | 本说明文档 |
| `reports/social/` | 排期、日报、周报输出 |
