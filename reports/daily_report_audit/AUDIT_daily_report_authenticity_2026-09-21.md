# ChinaBound Travel 日报真实性审计报告

| 项 | 值 |
| --- | --- |
| 被审计对象 | `reports/feishu_daily/daily_2026-09-22.json`（数据日期 2026-09-21，即用户提供的「每日运营日报」） |
| 审计日期 | 2026-09-22 |
| 审计方法 | 不复用日报数字。对每条声明重新取源：① 直接调用两条巡检管线的原始函数（`site_health_agent.py` / `feishu_daily_report.py` 的 `scan_content` 等价逻辑）② 读 `content/` front-matter ③ 读 `public/` 线上实际产物 ④ 读快照/登记表 ⑤ 重跑 `affiliate_link_audit.audit()` |
| 审计脚本 | `C:\temp\dsh\verify_report.py` / `verify2~7.py`（只读，未写仓库任何文件） |

---

## 0. 结论速览

| 维度 | 结果 |
| --- | --- |
| 报表底层数字可复现性 | ✅ **原始数字全部可复现**（GA4/GSC/MailerLite/Travelpayouts/文章数/tracking 覆盖率） |
| 报表数字与"日"标签的口径一致性 | ❌ **2 处错标**：OKR「日搜索曝光」实为 7 天窗口；`indexed_pages` 字段实为 sitemap 条数 |
| 日报「内容质量巡检」节 | ❌ **与站点健康巡检节直接冲突**：同一份报告里 `占位符 0 篇` 与「2 条 high 占位符问题」并存 |
| 日报所列站点问题 9 条 | ❌ **5 条误报（56%）**、2 条真实、1 条真实但定性错误、1 条阈值设定不当 |
| 日报未发现的线上缺陷 | 🔴 **7 个孤儿页（占线上 10.4%）+ 4 个 `<title>` 为裸 URL 的桩页** —— 日报完全没看到 |
| 「实验与阻塞」表 | ❌ **3 项状态与权威登记表矛盾**，且源文件已 15 天未更新 |
| 追踪闭环 | 🔴 **失效**：`execution_log.json` 显示该环节自 09-04 起反复执行数千次，累计 resolved ≈ 0，全部沉淀为 `need_manual` |
| 值得肯定的诚实设计 | ✅ 报告对 GA4 口径矛盾、渠道合计≠总量、28 天数据陈旧（最老 37 天）均有**主动自我标注**，未掩盖 |

**一句话**：这份日报的**取数环节是可信的，但"判读"环节不可信** —— 它会把 7 天值当成日值、把 sitemap 数当成索引量、把正则误截断的标题当成过短标题、把 HTML 表单属性当成占位符，并且漏掉线上真实存在的孤儿页。同时它的"分配→跟踪"环节是一个空转循环，分配了等于没分配。

---

## 1. 数据真实性核验（逐条）

### 1.1 已验证为真实（9 项）

| # | 日报声明 | 复现结果 | 判据 |
| --- | --- | --- | --- |
| 1 | 站点总文章数 64 篇 | ✅ 64 | `content/posts/*.md` 计数 = 64 |
| 2 | 今日新发 1 篇 | ✅ 1 | `2026-09-21-china-nightlife-guide-...md`，`date: 2026-09-21T10:00:00+08:00` |
| 3 | 联盟链接 tracking 覆盖率 211/211（🟢） | ✅ 211/211 | 重跑 `affiliate_link_audit.audit()` → `links_tracked=211, links_untracked=0`（8 个 key，`partnerizeUserId` 无 URL 但不计入链接） |
| 4 | GA4 访客 9 / 会话 13 / 页浏览 22 | ✅ 完全一致 | 与 `daily_2026-09-22.json` 字段逐一对齐 |
| 5 | 跳出率 100.0% / 互动率 0.0% / 平均时长 1分49秒 | ✅ 一致 | 同上 |
| 6 | 7 日滚动：会话 73 / 跳出率 50.7% / 互动率 49.3% / 88 秒 | ✅ 一致 | 同上 |
| 7 | GSC 7 天窗口：曝光 141 / 点击 0 / 平均排名 30.77 / CTR 0.00% | ✅ 一致 | `gsc_window_start=2026-09-13, end=2026-09-19` |
| 8 | 邮件订阅 总 24 / 昨日新增 0 | ✅ 一致 | `ml_available=true` |
| 9 | Travelpayouts 点击 12 / 订单 0 / 佣金 $0.00；inits「未上报」 | ✅ 一致 | `tp_inits=0` 被标为「未上报」而非「0 展示」，口径处理正确 |

### 1.2 真实但被错标口径（2 项 —— 属"数字对、标签错"）

**① OKR「日搜索曝光 141 次 vs 目标 13 次 → ✅100%」是虚假达标**

- 代码链：`feishu_daily_report.py:1280` → `okr_utils.build_okr_section()` → `extract_kr(data, "gsc_impressions")`
- `KR_ALIASES["gsc_impressions"] = ["gsc_impressions"]`，只认这一个字段，**没有任何窗口语义**
- 而 `gsc_impressions` 的实际值是 **2026-09-13 ~ 2026-09-19 的 7 天窗口**，且窗口结束于报告日前 2 天
- 后果：用 7 天累计值对比 `Q3 月目标 400 ÷ 30 = 13.3` 的日目标，**数学上必然 100%**。这不是达标，是单位错配。
- 报告其他部分其实已意识到这个问题（`feishu_daily_report.py:598` 注释：「缓存口径：28 天快照窗口独立成行，绝不冒充"昨日"（真实性修复）」），但**修复只覆盖了 28 天窗口，7 天窗口仍被当作"日"进 OKR**。

**② `indexed_pages` 字段名与语义不符**

- 报告渲染为「Sitemap 数量 1 个」——标签写对了
- 但数据层字段名叫 `indexed_pages`，来源是 `len(sitemaps["sitemap"])`（sitemap 索引条目数）
- 同一时点快照 `REPORTING_SNAPSHOT_2026-09-21.json:1337` 里真正的 `indexed_pages` = **69**
- 后果：任何下游（周报/月报/看板）若复用日报的 `indexed_pages` 字段，会把「1 个 sitemap」当成「只有 1 个页面被索引」，得出灾难性错误结论

### 1.3 「今日新增 1 篇 → 🟢 内容产出正常」的判读不成立

该篇文章（10,200 字符 / 9 个 H2 / 3 图 / 7 内链，篇幅本身合格）：

| 检查项 | 结果 |
| --- | --- |
| `summary` == `description` | ✅ **完全相同**（meta description 是模板填充句，非独立文案） |
| `description` 内容 | `"China Nightlife: Bars, Clubs, and Evening Culture for travelers visiting China. Practical guide for foreign travelers visiting China."` —— 与 `_draft/` 里被放弃的同类文章同一套模板句式 |
| 正文含联盟链接（`tpo.li`） | ❌ **无** —— 这篇新文章对本次会话的 12 次联盟点击贡献为 0 |
| 同题材历史尝试 | `_draft/` 下已有 2026-08-24、2026-08-25 两次同名尝试被放弃 |
| 日报 QA 能否抓到 description 问题 | ❌ 不能 —— 日报 QA 只匹配 `#TP_# / #VPN_# / PLACEHOLDER / [Image:`，模板填充型描述不在此列 |

> 修正说明：我初查时怀疑「`audit_status: pass2` 偏低」是缺陷，但实测 64 篇中 26 篇为 pass2、7 篇 pass4、31 篇无该字段 —— **pass2 是已发布文章的多数态，不构成缺陷**，故不作为问题上报。

---

## 2. 报告所列问题的真伪（问题真理）

### 2.1 站点健康巡检 9 条：5 条误报

全部 9 条来自 `reports/daily_issues/site_health_issues_2026-09-21.json`（`site_health_agent.py`）。我直接调用了它的原始函数复现，结果一致。

| 问题 | 判定 | 根因证据 |
| --- | --- | --- |
| `content_placeholder` × `content/contact.md`（high） | ❌ **误报** | 正文 3 处 "placeholder" 全部是 HTML `<input placeholder="John Smith">` 等**表单属性** |
| `content_placeholder` × `content/search.md`（high） | ❌ **误报** | 文件首字节是 **UTF-8 BOM (`\ufeff`)**，`re.match(r'^---\s*\n...')` 失配 → 整文件被当正文扫描 → 命中 YAML 键 `placeholder:`（Hugo 搜索模板的合法变量） |
| `title_too_short` × `xian-terracotta-army`（"2 字符"） | ❌ **误报** | 真实 title `"Xi'an Terracotta Army: Tickets & History"` = 40 字符；检查器正则在 `Xi'an` 的撇号处截断，只读到 `"Xi"` |
| `title_too_short` × `china-high-speed-rail`（"17 字符"） | ❌ **误报** | 真实 title = 58 字符；在 `China'S` 撇号截断 → `"How To Ride China"` |
| `title_too_short` × `foodies-guide-to-china`（"6 字符"） | ❌ **误报** | 真实 title = 44 字符；在 `Foodie's` 撇号截断 → `"Foodie"` |
| `title_too_short` × `content/success.md`（19 字符） | ✅ 真实 | `'Payment Successful!'` 确实 19 字符。但这是支付成功页，`TITLE_MIN=20` 对该页型不适用 |
| `meta_description_too_long` × `shanghai-beyond-the-bund`（166 字符） | ✅ 真实 | 实际 166 字符，超阈值 165 |
| `draft_leak` × `content/posts/2026-07-22-cultural-etiquette-guide.md`（high） | ⚠️ **真实但定性错误** | 该文件确为 `draft: true`，但其 `slug = cultural-etiquette-guide-aussie-kiwi`，线上**不存在**该路径页面（`public/` 无此目录）。真问题是「草稿文件被放在 `content/posts/` 而非 `content/_draft/`」的仓库卫生问题，**不是"已发布到线上"** |
| `multiple_analytics_destinations`（critical） | ✅ 真实 | GA4 Google Tag 配了 2 个 destination（`G-GECBME3YVJ` + `G-P6BH500VBK`），证据含页面 HTML 与 gtag 载荷 |

**误报根因汇总（3 个独立 bug）**

1. **`PLACEHOLDER_PATTERNS` 含 `re.compile(r'placeholder', re.IGNORECASE)`** —— 裸词匹配，必然命中 HTML `placeholder=` 属性与 YAML 键名。
2. **front-matter 正则 `re.match(r'^---\s*\n...')` 不容忍 BOM** —— 一个 BOM 字符就让整个 front-matter 解析失效，退化成本文扫描。
3. **title 提取正则 `[^\"'\n]+` 会在撇号处截断** —— 任何含 `'` 的英文 title（`Xi'an` / `China'S` / `Foodie's`）都会被截断成片段，进而误判过短。这是**系统性的、可复现的**误报来源，只要 title 带撇号就必现。

> 另外，`check_title_meta_length()` 完整运行返回 **12 条**（含 7 条 `meta_description_too_short`），而当日快照只落了 9 条 —— 说明快照与函数输出之间存在筛选/丢弃环节，且未被记录。

### 2.2 日报「内容质量巡检」节与站点巡检节自相矛盾

`feishu_daily_report.py:1895-1937` 的 `scan_content()`：

| 日报声称 | 实际情况 |
| --- | --- |
| `占位符残留 0 篇 ✅` | 在 `content/posts/*.md` 范围内**成立**；但扫描范围**只覆盖 `content/posts/`**，漏掉 `content/` 根级 13 个页面（`search.md` / `contact.md` / `pricing.md` / `subscribe.md` / `success.md` / `free-itinerary.md` 等）。而 Pipeline A 的命中点正是在 `search.md` 与 `contact.md` |
| `草稿待审 0 篇 ✅` | ❌ **假**。判定代码为 `if "_draft" in post.name.lower() or post.name.startswith("draft")` —— **只看文件名，不读 front-matter**。实测 `content/posts/` 内 `draft: true` 的实际文件有 1 个（`2026-07-22-cultural-etiquette-guide.md`），漏检 1 篇 |
| `空链接 0 处 / 图片缺 Alt 0 处` | ✅ 在本扫描范围内成立 |

**同一份报告里「占位符 0 篇 ✅」和「2 条 high 占位符问题」并存**，读者无法判断哪个是事实。这是两套扫描器并行、互不校验、结果直接拼接导致的。

### 2.3 日报没有发现的线上真实缺陷 🔴

这是本次审计**新增发现**，原报告完全没有覆盖。

线上 `public/posts/` 共 **67 个页面**，其中 **7 个（10.4%）在仓库里找不到已发布的源文件**：

**A. 真孤儿页（6 个，仓库无任何源文件）**

```
/posts/2026-05-26-is-china-safe-for-tourists-2026-honest-assessment/      <title> = Is China Safe for Tourists in 2026? Honest
/posts/2026-05-27-how-to-survive-chinese-train-station/                    <title> = Chinese Train Stations: Survival Guide for
/posts/2026-09-01-chinabound-travel-guide-2026-09-monthly-update/          <title> = https://www.chinaboundtravel.com/posts/...（裸 URL）
/posts/best-travel-insurance-china/                                        <title> = Top-rated Travel Insurance for China 2026
/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/  <title> = China Transportation 2026: Trains & Didi
/posts/is-china-safe-for-tourists-2026-honest-safety-assessment/           <title> = Is China Safe for Tourists in 2026?
```

**B. 仅由草稿源支撑的线上页（1 个）**

```
/posts/transportation-guide-guide/
  唯一源文件 = content/_draft/2026-06-06-...attempt1.md（draft: "true"，audit_status: pending，正文仅 2 字符）
  <title> = 裸 URL（指向 china-transportation-complete-guide-...）
```

**C. `<title>` 是裸 URL 的桩页（4 个）**

`2026-09-01-...-monthly-update` / `how-to-survive-chinese-train-station` / `is-china-safe-for-tourists-2026-honest-assessment` / `transportation-guide-guide`

**根因**：`hugo.toml` 未设置 `cleanDestinationDir`（默认 `false`），Hugo 构建**从不删除**已下线的页面。内容被改名、迁移、重写后，旧页面永久滞留在线上。

**危害**：
- 这些页面持续被 Google 收录与抓取，其中 5 个带正常标题的孤儿页**很可能正在获得排名与曝光**，而团队以为它们已下线
- `is-china-safe-for-tourists-2026-honest-assessment` 与 `...-honest-safety-assessment` **同时存在** —— 同一主题两个 URL，权重分流
- 日报「站点总文章数 64 篇」用的是 `content/posts/*.md` 文件数，线上真实是 67 页，**两个口径互不校验**
- 日报的 QA 扫描只扫 `content/`，**永远看不到 `public/` 里的孤儿**

### 2.4 「实验与阻塞」表：3 项与权威登记表矛盾

日报的状态来源是 `static/experiments.json`，其 `updated_at = 2026-09-06`（**已 15 天未更新**）。

| 实验 | 日报显示 | 权威登记表实际 |
| --- | --- | --- |
| **DRIVE-001** | 📋 PLANNED（并被列为「今日高优先级待办 #1 🔴 状态异常」） | `docs/AI_CONTEXT.md`：`RUNNING（start 2026-08-16，ACTIVE）`；`reports/revenue/EXPERIMENT_COMPARISON.csv`：`observation_days=1, status=INSUFFICIENT_SAMPLE, data_source=CACHED` |
| **REV002** | 📋 PLANNED | `reports/revenue/REV002_EXPERIMENT_REGISTRY.csv`：`status=RETIRED, decision=RETIRED_INVALID_INSTRUMENT`（**已退役**，非"待启动"） |
| **REV001** | 📋 PLANNED，观察 0d | `docs/AI_CONTEXT.md`：`RUNNING（start 2026-08-16）` —— 若真在跑，则是 **36 天 0 样本**，属埋点失效而非未启动 |

代码里已识别了一个方向的漂移（`feishu_daily_report.py:894-895` 注释：「快照里的 RUNNING 可能是漂移出来的幻影状态」），但**反向漂移**（`experiments.json` 陈旧 → 真实在跑的实验被显示为 PLANNED）没有任何处理。

**后果**：日报把 DRIVE-001 列为最高优先级待办 #1。若 Drive 实际已在跑，这是**假警报**，浪费了本应投入真正问题的排查精力；若确实未部署，则 `AI_CONTEXT.md` 与 `EXPERIMENT_COMPARISON.csv` 需要修正。两种情况下日报都没有给出正确判断依据 —— 它把一份 15 天前、且自相矛盾的文件当作事实输出，并在此基础上升级了告警等级。

### 2.5 报告已主动标注、应予肯定的部分

这些不是问题，而是**做得对的地方**，需要记录以免被后续"优化"掉：

- ✅ **GA4 口径矛盾自我标注**（`feishu_daily_report.py:560-583`）：明确指出「会话 13 / 页浏览 22 但互动率 0.0%」不可能同时成立，并给出正确下限（应 ≥ 69.2%），明确提示「该日均值可能来自不同查询口径或缓存，勿单独引用」
- ✅ **平均时长与互动率矛盾标注**：指出「互动率 0% = 无会话超 10 秒，则平均值不应 >10 秒」
- ✅ **渠道合计≠总量标注**：渠道会话 20≠13、渠道用户 12≠9、Top 页面 21≠22，并说明是 GA4 小样本下 session 维度与事件级总量的正常背离
- ✅ **低样本标注**：访客 9 < 10，百分比仅作参考
- ✅ **28 天数据陈旧标注**：明确「8 项指标仍是上一次观测日数值（最老 37 天）」
- ✅ **bot 流量剔除**：`/ops/ops-center` 等内部路径已从热门页榜单剔除（1 次）
- ✅ **`tp_inits` 口径处理**：标「未上报（点击>0，勿读作 0 展示）」，没有把缺失当 0

---

## 3. 追踪机制本身是失效的

`reports/daily_issues/execution_log.json` 是这套闭环唯一的执行记录，实测：

| 事实 | 数据 |
| --- | --- |
| 该文件时间跨度 | 2026-09-04 起，最后执行 09-22 |
| 执行轮次 | **数千次**（单 `task_2026-09-14_seo` 在 09-14 一天内被执行 ~30 轮，每小时一轮） |
| 累计 `resolved` | **≈ 0**（绝大多数轮次 `resolved=0`；`09-13` 起 seo 恒为 `resolved=2, need_manual=5`，反复 30+ 轮毫无变化） |
| 累计 `failed` | **0** |
| 所有 issue 最终状态 | 全部 `need_manual` / `manual_review` |

**根因在 `agent_task_executor.py` 的能力矩阵**：它只自动修复 3 类（`title_too_long` / `meta_description_too_short` / `ai_forbidden_word`），而 `daily_issue_router` 生成的 6 类问题里有 5 类（`content_placeholder` / `image_missing_alt` / `title_too_short` / `draft_leak` / `social_zero_engagement`）**代码里硬编码为 `need_manual`**。

**结果是一个空转循环**：调度器每 30 分钟唤醒 agent → agent 读同一个问题 → 判断"无法自动修"→ 写回 `need_manual` → 下一轮再重复。`execution_log.json` 增长到数千行，但没有任何问题被推进、关闭或升级。**分配了等于没分配**，而这个问题已经持续运行了 18 天。

---

## 4. 建议的处理顺序

| 优先级 | 问题 | 负责人 |
| --- | --- | --- |
| 🔴 P0 | 7 个孤儿页 + 4 个裸 URL 桩页（线上真实缺陷，影响 SEO 与品牌） | ops |
| 🔴 P0 | 实验登记表三方矛盾（DRIVE-001/REV002/REV001），并修正 `static/experiments.json`（15 天未更新） | ops |
| 🟠 P1 | title 撇号截断正则 bug（系统性误报源，凡 title 带 `'` 必现） | sitehealth |
| 🟠 P1 | `PLACEHOLDER_PATTERNS` 裸词匹配 + BOM 不兼容（误报源） | sitehealth |
| 🟠 P1 | `scan_content()` 只看文件名判草稿 + 只扫 `content/posts/`（漏报源） | sitehealth |
| 🟠 P1 | OKR 把 7 天 GSC 窗口当"日"值（虚假达标） | reports |
| 🟠 P1 | `indexed_pages` 字段语义错配（数据层隐患） | reports |
| 🟡 P2 | 追踪闭环空转（executor 能力矩阵与 router 产出严重不匹配） | ops |
| 🟡 P2 | `gsc_clicks_28d` / `gsc_impressions_28d` 已 37 天未刷新 | reports |
| 🟡 P2 | 新文章 meta description 与 summary 完全相同 + 无联盟链接 | content |
| 🟢 P3 | 2 条真实 SEO 问题：`success.md` 标题 19 字符（阈值对支付页不适用）、`shanghai-beyond-the-bund` 描述 166 字符 | seo |
| 🟢 P3 | 仓库卫生：`content/posts/` 内的 draft 应移入 `_draft/`；`_draft/` 31 篇草稿中 12 篇 slug 与已发布文章同名 | content |

---

## 5. 遗留与设计偏差

**本次审计的边界（明确声明，避免过度解读）**

1. **未验证的项**：GA4/GSC/MailerLite/Travelpayouts 的**上游真实值**无法在本机复核（需访问 Google/MailerLite/Travelpayouts 后台）。本次只验证了「日报数字与其引用的本地数据文件一致」，未验证「本地数据文件与第三方后台一致」。报告自述的「GA4 来源未证实（measurement ID 与数值 ID 无交叉验证）」「NordVPN 未接入」两条自我标注在此范围内依然有效。
2. **未修改任何仓库文件**：全程只读。未运行 `site_health_agent`（会写 `reports/`）、未跑 pytest（已知会改写 12 个保护区文件）、未构建 Hugo、未 git 操作。
3. **未执行任何修复**：包括孤儿页清理、`cleanDestinationDir` 配置、正则修复。这些都属受保护区域或需线上验证，须由对应 agent 授权后执行。
4. **孤儿页判定方法有近似**：Hugo 的 slug 解析按「显式 `slug:` 优先，否则取文件名去日期前缀」近似实现，与 Hugo 官方规则可能有细微差异。6 个"真孤儿页"已逐个核对：其 slug 在 `content/` 全树中确实不存在任何源文件，结论稳健。
5. **`pass2` 不是缺陷**：初查曾怀疑新文章 `audit_status: pass2` 偏低，实测 pass2 是已发布文章多数态（26/33），已撤回该判断。
6. **`draft_leak` 定性已修正**：初查曾判断为「slug 碰撞」，实测该草稿 slug 为 `cultural-etiquette-guide-aussie-kiwi`，与已发布的 `cultural-etiquette-guide` 不同，线上无该页面 —— 故为仓库卫生问题，非线上泄露。
7. **临时脚本位置**：`C:\temp\dsh/verify_report.py`、`verify2.py` ~ `verify7.py` 位于仓库外，未污染工作区（`site-health-daily.yml` 用 `git add -A`，仓库内不留临时文件）。
