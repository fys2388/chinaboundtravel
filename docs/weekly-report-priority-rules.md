# 周报风险分级规则（Weekly Report Priority Rules）

> 版本：2026-09-28 · 触发来源：第 39 周周报分析
> 关联脚本：`scripts/feishu_weekly_report.py` · `_detect_risk_level` + `_generate_next_week_plan`
>
> 本文件是「周报优先级算法」的规范说明，供后续人工维护者与未来 agent 参考。
> 新增风险项必须先在此登记，再落到代码，避免"算法漏判"。

---

## 1. 分级阈值表

| 触发条件 | 分级 | 报告位置 | 对应行动 |
|---|---|---|---|
| GSC 零收录（`indexed_pages == 0` 且 `gsc_ok`） | 🔴 red | 本周风险汇总 → 基建止血 | GSC 验证域名 + 提交 sitemap |
| **GSC 已授权但 `sitemap_count == 0`**（新增 · 2026-09-28） | 🔴 red | 本周风险汇总 → 基建止血 | 调用 `gsc-automation.py` 提交 sitemap + 抽样 URL Inspection |
| **Top 页面中 404 浏览量占比 ≥ 20% 且绝对量 ≥ 5**（新增 · 2026-09-28） | 🔴 red | 本周风险汇总 → 基建止血 | 全量检测内部断链 + 修复跳转失效的内链 |
| **Top 页面中 404 浏览量占比 ≥ 10% 且绝对量 ≥ 3**（新增 · 2026-09-28） | 🟡 yellow | 本周风险汇总 | 抽查 3-5 条最热外链与内链来源 |
| GSC 未授权 / API 异常 | 🟡 yellow | 本周风险汇总 | 检查 GSC 服务账号授权 |
| 联盟佣金 = 0 且覆盖率 < 30% | 🟡 yellow | 本周风险汇总 | 提交 sitemap 前先确认链接追踪 |
| 人设年限冲突 > 0 篇 | 🟡 yellow | 本周风险汇总 | 批量迁移 legacy 文案 |
| 周访客 < 100 | 🟡 yellow | 本周风险汇总 | 发布高转化长尾攻略 |
| 跳出率 > 60% | 🟡 yellow | 本周风险汇总 | 优化页面内容质量 |
| 平均停留 < 30 秒 | 🟡 yellow | 本周风险汇总 | 优化核心文章内容 |
| 邮件订阅新增 = 0 | 🟡 yellow | 本周风险汇总 | 上线免费订阅诱饵 |
| 结构化数据缺失 > 5 篇 | 🟡 yellow | 本周风险汇总 | 批量补 Article Schema |

**阈值原则**：
- 绝对量下限（≥3 或 ≥5）防止低流量周误报——1 个 404 页 1 次浏览不算事故。
- 占比 + 绝对量双重判定，占比单独用容易被极端值扭曲。

## 2. 404 检测规则（P0-1）

**判定范围**：`data["top_pages"]`（GA4 按浏览量排序的前 10 个页面）。

**404 页面识别（4 条任一命中即计入）**：
- `title` 含 `404`
- `title` 含 `page not found`
- `path` 含 `/404`
- `path` 含 `/page-not-found`

**占比计算**：
```
rate = sum(views of 404 pages) / max(week_pageviews, 1) × 100
```
`week_pageviews` 缺失时回退到 `sum(views of all top_pages)`。

**为什么放在 Top10 而不是全站**：全站没有 404 计数通道；Top10 是数据管线里唯一能稳定拿到"标题+浏览量"的组合。缺点是最深处的 404 页面无法覆盖，但 Top10 已经足够捕捉用户真实摩擦。

## 3. Sitemap 提交规则（P0-2）

**触发条件**：`gsc_ok and gsc_data["sitemap_count"] == 0`

**独立于 indexed_pages 的原因**：sitemap 未注册 ≠ 零收录。GSC 可以爬到一个 URL 并展示曝光（例如 27 页），但只要 sitemap 未注册，GSC 就不知道站内还有其他 30+ 篇文章。旧逻辑把两者绑在一起，是"曝光 27 页 / 已提交 0 页"漏检的直接根因。

**反例保护**：
- GSC 未授权时不触发（因为没连上 API 拿不到 sitemap_count，`gsc_ok=False` 已过滤）。
- sitemap_count > 0 时不触发。

## 4. 下周计划映射（P0-3，2026-09-28 v4 重构）

`_generate_next_week_plan(risks, data)` 已重构为**按实际状态条件过滤**，不再"红风险触发时 dump 全部"。

**High 优先级（基建止血）过滤规则：**

| 任务 | 触发条件 | 跳过条件（视为已完成） |
|---|---|---|
| 修复 404 断链 | `_404_rate >= 10%` 且 `_404_views >= 3` | — |
| Cloudflare 301 重定向 | `REDIRECTS_PATH` 不存在 | `static/_redirects` 已存在 |
| OG / Twitter Card 标签 | `META_TAGS_PATH` 不存在 | `layouts/partials/head/meta.html` 已存在 |
| GSC 提交 sitemap | `gsc_ok and (indexed_pages==0 or sitemap_count==0)` | GSC 已授权且 sitemap_count>0 |
| Joran 年限文案修正 | `posts_with_conflict > 0` | 冲突数为 0 |
| 联盟链接覆盖 | `coverage < 95% and not site_wide_affiliate` | 站点级模板覆盖已启用，或覆盖率 ≥95% |
| 深度优化 2 篇核心文章 | `posts_without_schema > 5 and not template_level_coverage` | Schema 覆盖率达标 |

**Medium 优先级（增长配套）**：当 risks 含 yellow 时保持原逻辑，5 项一律加入。

**Low 优先级（常规运维）**：`文章页批量补充 Article 结构化数据` 条件化为 `posts_without_schema > 0 and not template_level_coverage`；`全量检测内部断链与占位符` 保持无条件加入（作为基线扫描）。

**收益对比（W39 真实数据）**：
- 旧逻辑：red risk 触发 → 无条件 dump 7 项 high 任务（含已完成的 301/OG/Joran/联盟）
- 新逻辑：仅 2 项 high（404 修复 + GSC sitemap），4 项已完成任务不再重复出现

## 5. SEO 段"已提交 sitemap"动态化（P0-4）

**修复前**：`"已提交 0 页 / GSC 曝光页面 ..."` 是字面量字符串，无论 GSC 实际状态如何永远显示"已提交 0 页"。

**修复后**：
```python
_sitemap_count = gsc_data.get("sitemap_count")
_sitemap_display = "-" if _sitemap_count is None else str(_sitemap_count)
# f-string: 已提交 sitemap {_sitemap_display} 个
```

未授权 / API 错误时 `sitemap_count` 不存在，显示 `-` 而非伪造 `0`。

## 6. 未在本轮处理的项（P1/P2，登记待办）

以下问题在本次周报分析中被识别，处理状态在下方标注（2026-09-28 v4 更新）：

| ID | 位置 | 问题 | 状态 | 处理 |
|---|---|---|---|---|
| P1-OKR-100CAP | `okr_utils.build_okr_section` | 55 人 / 目标 47 人 → 进度显示 100% | **误判 · 已处理** | 代码 L286-290 已生成 note `"进度封顶 100%（目标偏低）"`。目标校准属于运营动作。 |
| P1-DISCONNECTED | OKR 段 | "未连接"标 ⚪ 掩盖"数据管道缺失" | **误判 · 设计如此** | 代码 L242-253 注释明确："NOT_AVAILABLE 不显示 0，不进入红灯"，⚪ 是刻意决策。 |
| P1-PUBLISH-MATCHER | `okr_utils._plan_judge` (L389) | `"发布" and "文章"` 匹配条件太窄，W39 "攻略" 任务名永远漏匹配 | **已修复 · 2026-09-28** | 加宽为 `"发布" and ("文章" or "攻略" or "篇" or "内容")`。 |
| P2-CONCLUSION | `conclusions` / `priority_actions` | 404 未纳入 `priority_actions` | **已修复 · 2026-09-28** | 见 §7 v2。 |
| P2-DIRECT-REMARK | `channel_rows` | Direct 固定写"停留时长优质"与 3 秒真实数据矛盾 | **已修复 · 2026-09-28** | 见 §7 v2。 |
| P2-REVIEW-STUCK | `okr_utils.review_previous_plan` | 连续 2 周 20% 完成的任务永远显示"进行中" | **已修复 · 2026-09-28** | 加载 W-1/W-2 快照计算连续未完成周数，N≥2 追加 "🔴 连续 N 周未完成"。见 §7 v3。 |
| P0-PLAN-PRUNE | `_generate_next_week_plan` | red risk 触发时无脑 dump 7 项 high 任务，包括已完成的 301/OG/Joran/联盟 | **已修复 · 2026-09-28** | 按 `REDIRECTS_PATH` / `META_TAGS_PATH` / `sitemap_count` / `posts_with_conflict` / `coverage` / `posts_without_schema` 实际状态过滤，W39 场景下 high 从 7 项缩减到 2 项。见 §7 v4。 |

**唯一剩余待处理项**：无。所有登记问题均已修复或明确撤回。

## 7. 变更历史

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-09-28 | v1 | 首次固化规则文档；落地 P0 修复 4 项（404 检测、sitemap=0 检测、404 任务入 plan、SEO 段动态化） |
| 2026-09-28 | v2 | 落地 P2 修复 2 项（P2-CONCLUSION 404/sitemap 纳入核心优先级；P2-DIRECT 移除"停留时长优质"硬编码）；撤回 2 项误判（P1-OKR-100CAP、P1-DISCONNECTED） |
| 2026-09-28 | v3 | 落地 P2-REVIEW-STUCK（加载 W-1/W-2 快照计算连续未完成周数）+ 新发现 P1-PUBLISH-MATCHER 修复（`_plan_judge` 加宽"攻略/篇/内容"匹配） |
| 2026-09-28 | v4 | 落地 P0-PLAN-PRUNE：重构 `_generate_next_week_plan(risks, data)`，high 优先级任务改为按实际状态条件过滤（404 率 / REDIRECTS_PATH / META_TAGS_PATH / sitemap_count / posts_with_conflict / coverage / posts_without_schema），W39 场景下 high 从旧逻辑 7 项缩减到 2 项（404 + GSC） |
