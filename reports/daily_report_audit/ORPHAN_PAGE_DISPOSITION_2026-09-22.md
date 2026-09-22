# 孤儿页逐页处置清单

- **生成日期**：2026-09-22
- **数据日**：GSC 快照 2026-08-21~2026-09-19（3 份 28 天窗口叠加）
- **口径**：`public/posts/` 实测枚举 × `content/` 全树 slug 比对 × GSC 页面级曝光
- **性质**：**只读清单，未做任何修改**。执行处置需另行授权。
- **上游工单**：AUDIT-OPS-001

---

## ⚠️ 对审计原结论的修正（重要）

原审计（`AUDIT_daily_report_authenticity_2026-09-21.md` §2.3）称线上有 **7 个孤儿页（6 真孤儿 + 1 草稿支撑）**，并断言「5 个带正常标题的孤儿页很可能正在获得排名与曝光」。

**实测只有 4 个真孤儿页（3 无源 + 1 仅草稿支撑），不是 7 个。**

3 个被误判为「无源」的页面其实**有有效的已发布源文件**：

| 页面 | 原审计判定 | 实测 |
|---|---|---|
| `/posts/best-travel-insurance-china/` | A 真孤儿页 | `content/posts/best-travel-insurance-china.md`（12,213 字节，259 行，title 正常） |
| `/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/` | A 真孤儿页 | `content/posts/2026-07-16-china-transportation-...md`（18,680 字节，272 行） |
| `/posts/is-china-safe-for-tourists-2026-honest-safety-assessment/` | A 真孤儿页 | `content/posts/2026-07-16-is-china-safe-...md`（13,956 字节，223 行） |

### 根因：front-matter 格式漏检

这 3 个文件使用 **TOML front-matter（`+++`）**，不是 YAML（`---`）：

```
+++
content_id = "cbt-d701fb08eb7b"
title = "Top-rated Travel Insurance for China 2026"
date = 2026-06-21
```

原审计的 slug 解析只匹配 `^---\s*\n`，遇到 `+++` 直接判为「无 front-matter」，因此无法把文件归属到对应 slug，从而把它们错报成孤儿页。

**`content/` 下有 19 个 TOML front-matter 文件**（125 个已发布源文件中占 15.2%），其中 3 个在 `content/posts/`：

```
content/cities/{beijing,chengdu,guilin,hangzhou,shanghai,western-sichuan,xian,yangshuo}.md
content/{disclaimer,privacy-policy}.md
content/{about,guides,resources}/_index.md
content/posts/{best-travel-insurance-china, 2026-07-16-china-transportation-..., 2026-07-16-is-china-safe-...}.md
```

**同一个漏检存在于 `site_health_agent.py` 的 9 处 YAML-only 正则**（行 127、207、421、451、493、532、570、1040，以及本轮新增的 `split_front_matter`）。即：巡检器对全部 19 个 TOML 文件是隐形的 —— 它们的 title 长度、meta description、占位符、禁用词全部没被检查过。**已登记为 AUDIT-FE-008。**

### 曝光影响面的修正

原审计称「5 个带正常标题的孤儿页很可能正在获得排名与曝光」。实测 4 个真孤儿页中**只有 1 个**在 28 天窗口内有任何曝光，且仅 **6 次**：

| 页面 | 28d 曝光 | 点击 | 平均位置 |
|---|---|---|---|
| `/posts/2026-05-26-is-china-safe-for-tourists-2026-honest-assessment/` | **6** | 0 | 86.5 |
| `/posts/2026-05-27-how-to-survive-chinese-train-station/` | 无记录 | — | — |
| `/posts/2026-09-01-chinabound-travel-guide-2026-09-monthly-update/` | 无记录 | — | — |
| `/posts/transportation-guide-guide/` | 无记录 | — | — |

**SEO 危害被原审计高估了。** 4 个孤儿页累计只有 6 次曝光、0 次点击、平均位置 86.5（第 87 名，实际上没人看得见）。

不过审计关于**机制危害**的判断依然成立：`hugo.toml` 未设 `cleanDestinationDir`，Hugo 从不删除下线页面，孤儿页会永久滞留。且 `daily_issue_router` 的 QA 只扫 `content/`，永远看不到 `public/` 的孤儿。

---

## 逐页清单

`public/posts/` 共 **68 个目录**，排除 `/posts/page/`（Hugo 分页容器，下含 `1`~`7` 分页目录，非文章页），实际文章页 **67 个**。

### 真孤儿页（4 个）

| # | 页面 | 线上标题 | 源文件状态 | 28d 曝光 | 建议处置 |
|---|---|---|---|---|---|
| 1 | `/posts/2026-05-26-is-china-safe-for-tourists-2026-honest-assessment/` | `Is China Safe for Tourists in 2026? Honest`（正常） | 无源 | 6 / 0 点击 / 位置 86.5 | **301 到同主题已发布页** `/posts/is-china-safe-for-tourists-2026-honest-safety-assessment/`（14 曝光，位置 71.3）—— 主题重复且 slug 相近，权重应合并 |
| 2 | `/posts/2026-05-27-how-to-survive-chinese-train-station/` | `Chinese Train Stations: Survival Guide for...`（正常） | 无源 | 无记录 | **先查 GSC 全历史再定**。无 28d 曝光不等于从未有曝光；若历史上无曝光则直接下线，若有则 301 到 `/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/` |
| 3 | `/posts/2026-09-01-chinabound-travel-guide-2026-09-monthly-update/` | **裸 URL** | 无源 | 无记录 | **直接下线**。这是 2026-09 月报的早期版本残骸（正常页是 `/posts/chinabound-travel-guide-2026-09-monthly-update/`，已发布、无 GSC 曝光）。裸 URL 标题说明 Hugo 从没给它生成过正常内容 |
| 4 | `/posts/transportation-guide-guide/` | **裸 URL** | 仅草稿：`content/_draft/2026-06-06-transportation-guide-guide-attempt1.md`（`draft=true`，正文仅 2 字符，`audit_status: pending`） | 无记录 | **下线 + 删除草稿**。slug 本身就是拼写错误（`guide-guide`），且裸 URL 指向 transportation-complete-guide。草稿无价值 |

### `<title>` 为裸 URL 的桩页（4 个，与孤儿页部分重叠）

原审计列了 4 个，实测也是 4 个，但**构成不同**：

| # | 页面 | `<title>` 指向 | 是否孤儿 |
|---|---|---|---|
| 1 | `/posts/2026-09-01-chinabound-travel-guide-2026-09-monthly-update/` | 自身路径 | 🔴 孤儿 |
| 2 | `/posts/how-to-survive-chinese-train-station/` | `/posts/china-transportation-complete-guide-.../` | 已发布（11 字符 slug 差异） |
| 3 | `/posts/is-china-safe-for-tourists-2026-honest-assessment/` | `/posts/is-china-safe-for-tourists-2026-honest-safety-assessment/` | 已发布 |
| 4 | `/posts/transportation-guide-guide/` | `/posts/china-transportation-complete-guide-.../` | 🔴 孤儿 |

**关键差异**：原审计把这 4 个列为「桩页」，但实测其中 2 个（#2、#3）是**有已发布源文件的正常页面**，只是 `<title>` 被写成了另一路径的 URL。这不是桩页，而是 **canonical 迁移残留**：内容已搬到新 slug，旧 slug 仍在产出页面且 title 指向新地址。

建议处置：
- **#2、#3**：确认旧 slug 是否还需要保留。若需要，title 应改回自身内容（裸 URL 会伤害 CTR 和品牌展示）；若不需要，改为 301。这两个页面在 GSC 28 天窗口内**均无曝光记录**，下线风险低。
- **#1、#4**：见上方孤儿页处置建议。

### 非孤儿但值得注意的重复主题

| 主题 | slug A | slug B |
|---|---|---|
| 中国安全 | `/posts/is-china-safe-for-tourists-2026-honest-safety-assessment/`（14 曝光，已发布） | `/posts/is-china-safe-for-tourists-2026-honest-assessment/`（裸 URL，已发布） |
| 交通指南 | `/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/`（297 曝光，已发布，位置 28.1） | `/posts/how-to-survive-chinese-train-station/` + `/posts/transportation-guide-guide/`（均裸 URL） |
| 月报 | `/posts/chinabound-travel-guide-2026-09-monthly-update/`（已发布） | `/posts/2026-09-01-chinabound-travel-guide-2026-09-monthly-update/`（孤儿，裸 URL） |

同一主题多 slug 会造成权重分流，属 AUDIT-SEO-002 / AUDIT-SEO-003 的范畴。

---

## `/posts/page/` 不是孤儿页

`public/posts/page/` 下有 `1`~`7` 七个子目录，是 **Hugo 分页产物**（文章列表分页），不是缺源内容的孤儿页。任何孤儿页统计都应排除它，否则会虚增 1 个。

---

## 执行前置条件（未满足前不建议动手）

1. **逐页查 GSC 全历史曝光**（不只是 28 天窗口）。28 天无曝光 ≠ 从未有曝光。特别是 #2 `/posts/2026-05-27-how-to-survive-chinese-train-station/`。
2. **确认 `cleanDestinationDir` 的影响面**：开启后 Hugo 会在下次构建时删除 `public/` 中所有不再由源文件产出的页面，可能误删非 Hugo 生成的静态资源。需先做一次 dry-run diff。
3. **确认 301 目标**：上表 301 目标均为已发布页，但需确认它们仍是最新权威版本。
4. **TOML 漏检先修**（AUDIT-FE-008）。在巡检器修好前，任何「孤儿页已清完」的判定都可能重演本次误判。

---

## 核验方法（可复现）

数据源都在仓库内，逻辑如下：

1. **线上页面**：枚举 `public/posts/` 下的目录，排除 `page`（Hugo 分页容器）。
2. **源归属**：遍历 `content/**/*.md`（排除 `_draft/` 与 `.audit_backup/`），
   解析 front-matter 的 `slug` 字段；**必须同时支持 TOML（`+++`）与 YAML（`---`）**，
   否则 19 个 TOML 文件会被漏掉（见 AUDIT-FE-008）；无 `slug` 时回退到文件名去日期前缀。
   线上页 slug 在此集合中找不到即判定为孤儿。
3. **GSC 交叉匹配**：`reports/seo/gsc_page_snapshots/INDEX_PAGE_SNAPSHOT_2026-09-{17,18,19}.json`，
   每份为 28 天窗口（窗口起点相差 1 天）。`pages` 是 `{完整 URL: {clicks, impressions, position}}`
   字典。本文的曝光数为三份累加，**不是去重后的 28 天真实值**，仅作量级判断；
   精确判断需去 GSC 后台查该 URL 的全历史。
4. **裸 URL 标题**：读每个 `public/posts/*/index.html` 的 `<title>`，
   匹配 `^https?://` 即判定为裸 URL。
5. **front-matter 格式分布**：读每个文件首字节，`+++` 开头为 TOML，`---` 开头为 YAML。

本次实测命令在会话内执行（脚本位于 `C:\temp\dsh\`，仓库外，已按仓库纪律清理），
关键数字为：67 篇文章页 / 4 个无源 / 19 个 TOML 文件 / 4 个裸 URL 标题页。
