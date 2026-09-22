# ChinaBound Travel 日报 · 需优化项清单

| 项 | 值 |
| --- | --- |
| 来源 | `reports/daily_report_audit/AUDIT_daily_report_authenticity_2026-09-21.md` |
| 数据日期 | 2026-09-21（日报文件 `reports/feishu_daily/daily_2026-09-22.json`） |
| 整理日期 | 2026-09-22 |
| 台账 | `reports/daily_report_audit/ISSUE_TRACKING_LEDGER_2026-09-21.json`（15 项待办 + 6 项误报关闭） |
| 排序规则 | 先修「让报告可信」，再修「报告指出的业务问题」——误报的报告比没有报告更危险 |

---

## 概览

| 层 | 含义 | 项数 | 其中 P0/P1 |
| --- | --- | --- | --- |
| A 层 | **日报/报表系统自身**需要优化的地方 | 7 | 4 |
| B 层 | **巡检与追踪机制**需要优化的地方 | 4 | 2 |
| C 层 | **报告指出的业务侧**优化项（报告本身没暴露的新缺陷） | 4 | 2 |
| D 层 | **报告覆盖缺口**——应新增监控的项 | 4 | 0 |
| **合计** | | **19** | **8** |

---

# A 层：日报/报表系统自身（7 项）

这一层的问题不是「日报报错了某个数字」，而是**日报的判读口径有缺陷**——数字取数正确，但贴的标签或对比基准是错的。

## A1 · 🟠 OKR 用 7 天 GSC 窗口冒充「日搜索曝光」—— 虚假达标

| | |
| --- | --- |
| 现状 | OKR 行「日搜索曝光 141 次 vs 目标 13 次 = ✅100%」。141 实为 2026-09-13~09-19 的 **7 天窗口值**，窗口结束于报告日前 2 天；日目标 = Q3 月目标 400 ÷ 30 = 13.3 |
| 为什么错 | 7 天累计值对比日目标，**数学上必然 100%**。这不是达标，是单位错配。读者会以为搜索基本盘已达标 |
| 根因 | `scripts/okr_utils.py:24` `KR_ALIASES["gsc_impressions"] = ["gsc_impressions"]` —— 只认一个字段、**无任何窗口语义**。链路 `feishu_daily_report.py:1280 → build_okr_section() → extract_kr()` |
| 优化动作 | ① 在 data 中拆分 `gsc_impressions_1d / _7d / _28d`；② 日度折算只用单日值，**无单日值时输出 `NOT_AVAILABLE` 而不是拿 7 天值顶替**；③ 若必须用窗口值则目标按同窗口折算并在行内标注窗口；④ 同步检查 traffic / content / revenue 三个 KR 是否有同类错配 |
| 完成判据 | 日报 OKR「日搜索曝光」不再出现 7 天窗口值；无单日数据时该行显示 `NOT_AVAILABLE` |
| 台账 id | `AUDIT-FE-004` |

## A2 · 🟠 `indexed_pages` 字段名与语义不符——数据层隐患

| | |
| --- | --- |
| 现状 | 日报字段 `indexed_pages` = 1，渲染为「Sitemap 数量 1 个」（标签写对了）。但值实际是 `len(sitemaps["sitemap"])` |
| 为什么错 | 同一时点快照 `REPORTING_SNAPSHOT_2026-09-21.json:1328-1337` 里**真正的 `indexed_pages` = 69**。两个字段同名不同义 |
| 危害 | 任何下游（周报/月报/季报/年报/看板/测试用例）复用该字段名，会把「1 个 sitemap」读成「只有 1 个页面被索引」，得出灾难性结论 |
| 优化动作 | 拆分字段：日报改名为 `sitemap_count`，另从快照取 `indexed_pages`。改名后同步检查全部下游消费者的字段引用 |
| 完成判据 | 两个字段各表其义，无下游歧义 |
| 台账 id | `AUDIT-FE-005` |

## A3 · 🟠 两套扫描器并行且互不校验——同一份报告自相矛盾

| | |
| --- | --- |
| 现状 | 同一份日报同时出现「占位符残留 0 篇 ✅」与「2 条 high 占位符问题」 |
| 根因 | `feishu_daily_report.py:1895-1937` 的 `scan_content()` 与 `site_health_agent.py` 是**两套独立扫描器**，扫描范围不同、判定口径不同、结果直接拼接 |
| 优化动作 | 收敛为**单一扫描实现**：两者共用同一份 front-matter 解析、同一份正则、同一扫描范围。这是 A3/A4/A5 的共同前置 |
| 完成判据 | 日报内不再出现互斥结论 |
| 台账 id | `AUDIT-FE-003`（部分） |

## A4 · 🟠 `scan_content()` 两个盲区——草稿判定只看文件名

| | |
| --- | --- |
| 盲区① | `if "_draft" in post.name.lower() or post.name.startswith("draft")` —— **只看文件名，从不读 front-matter 的 `draft` 字段**。实测 `content/posts/2026-07-22-cultural-etiquette-guide.md` 是 `draft: true`，被误判为已发布 → 日报「草稿待审 0 篇」是假的，漏检 1 篇 |
| 盲区② | 扫描范围仅 `content/posts/*.md`，**漏掉 `content/` 根级 13 个页面**（`search.md` / `contact.md` / `pricing.md` / `subscribe.md` / `success.md` / `free-itinerary.md` / `cancel.md` / `affiliate-disclosure.md` / `disclaimer.md` / `privacy-policy.md` / `refund-policy.md` / `terms-of-service.md`）——而 A6 的两条占位符命中**正好落在这两个未扫描文件里** |
| 优化动作 | ① 草稿判定改为读 front-matter（与 site_health_agent 口径对齐）；② 扫描范围扩到 `content/` 全树，排除 `_draft / .archived / .audit_backup` 等点号目录 |
| 完成判据 | `pending_posts` 由 0 修正为 1；扫描覆盖根级 13 页 |
| 台账 id | `AUDIT-FE-003` |

## A5 · 🟡 日报「站点总文章数」与线上真实页面数互不校验

| | |
| --- | --- |
| 现状 | 日报取 `content/posts/*.md` 文件数 = 64；线上 `public/posts/` 真实 **67 页** |
| 危害 | 两个「文章总数」口径互不校验，差 3 页无人发现（详见 C1）。这是 C1 之所以能存在 18 天而无人察觉的原因 |
| 优化动作 | 日报新增一行对账：`线上页面数 = 仓库源文件数 + 已登记孤儿页数`，不等时告警 |
| 完成判据 | 64 vs 67 的差异在日报中可见并被解释 |
| 台账 id | `AUDIT-OPS-001`（关联） |

## A6 · 🟢 「今日新增 1 篇 → 🟢 内容产出正常」的判读不含质量维度

| | |
| --- | --- |
| 现状 | 该篇 `summary == description`（逐字相同），内容为模板填充句；正文不含任何 Travelpayouts 联盟链接（无 `tpo.li`） |
| 为什么算缺陷 | 篇幅本身合格（10,200 字符 / 9 个 H2 / 3 图 / 7 内链），但 description 不是独立文案，且该篇对当日 12 次联盟点击贡献为 0 |
| 根因 | 日报 QA 只匹配 `#TP_# / #VPN_# / PLACEHOLDER / [Image:`，**抓不到模板填充型 description** |
| 优化动作 | ① 为该文补独立 meta description（≤160 字符，与 summary 不同）；② 日报 QA 增加「`description == summary`」与「描述与 slug 重复率」检查；③ 评估是否加联盟位——**但 CTA/联盟位变更可能落入 REV001/REV002 冻结范围，须先确认实验状态（见 C2）再动** |
| 说明 | `audit_status: pass2` **不是缺陷**——实测 64 篇中 pass2=26 / pass4=7 / 无该字段=31，pass2 是已发布文章多数态 |
| 完成判据 | `description != summary` 且长度 70–160 字符 |
| 台账 id | `AUDIT-CT-001` |

## A7 · 🟢 「草稿待审」指标语义混淆

| | |
| --- | --- |
| 现状 | 日报把「草稿」当风险项报告，但混用了两种不同性质的问题：① `content/_draft/` 下 31 篇正常草稿；② `content/posts/` 下 1 篇放错目录的草稿 |
| 优化动作 | 区分「未发布草稿数」（正常业务指标）与「草稿被放在发布目录」（仓库卫生告警）。后者应单独报 |
| 完成判据 | 日报有两个独立指标，不再把 31 篇正常草稿当卫生问题 |
| 台账 id | `AUDIT-CT-002` |

---

# B 层：巡检与追踪机制（4 项）

这一层是**产出这些告警的系统本身有问题**。它排在前面的原因：不先修误报源，后面所有「自动修复」都会执行错误改动。

## B1 · 🟠 title 提取正则在撇号处截断——系统性误报源

| | |
| --- | --- |
| 现状 | `scripts/site_health_agent.py` 的 title 提取正则遇到带英文撇号的 title 会截断，进而误报 `title_too_short` |
| 实测 3 例 | `2026-06-30-xian-terracotta-army-...`：报 2 字符，真实 `"Xi'an Terracotta Army: Tickets & History"` = 40 → 截断到 `"Xi"`<br>`2026-05-25-china-high-speed-rail-...`：报 17，真实 = 58 → 截断到 `"How To Ride China"`<br>`2026-07-23-foodies-guide-to-china-...`：报 6，真实 = 44 → 截断到 `"Foodie"` |
| 性质 | **系统性、可复现**：凡 title 带 `'` 必现。同一正则也污染了 meta description 长度检查 |
| 优化动作 | 改用 front-matter 解析器（PyYAML 或项目已有解析函数）读取 title/description，不用正则切引号。修复后跑全量检查 |
| 完成判据 | `check_title_meta_length()` 的 `title_too_short` 从 4 条降为 **1 条**（仅 `content/success.md` 保留） |
| 台账 id | `AUDIT-FE-001` |
| ⚠️ | **阻塞 B4 的方案 B**：不先消除误报源，扩展自动修复会把误报自动执行成错误改动 |

## B2 · 🟠 占位符检测两个缺陷叠加——2/2 告警全为误报

| | |
| --- | --- |
| 缺陷① | `PLACEHOLDER_PATTERNS` 含 `re.compile(r'placeholder', re.IGNORECASE)` —— 裸词匹配，必然命中 HTML 属性 `placeholder="..."` 与 YAML 键名 `placeholder:` |
| 缺陷② | front-matter 正则 `re.match(r'^---\s*\n...')` **不容忍 UTF-8 BOM**。一个 `\ufeff` 就让 front-matter 解析整体失效，退化成本文扫描 |
| 实测 | `content/contact.md`：3 处命中全是 HTML `<input placeholder="...">` 表单属性<br>`content/search.md`：文件首字节为 BOM，正则失配，整文件被当正文，命中 YAML 键 `placeholder:`（Hugo 搜索模板的合法变量） |
| 优化动作 | ① 收紧模式到真正的占位符形态（`{{...}}`、`<PLACEHOLDER>`、`TODO:`、`[Image: ...]` 等**有边界**的模式），裸词匹配必须**先剥离 HTML 标签再扫描**；② 读取时用 `utf-8-sig` 或 strip 掉 BOM |
| 完成判据 | `check_content_placeholders()` 的 `content_placeholder` 从 2 条降为 **0 条** |
| 台账 id | `AUDIT-FE-002` |

## B3 · 🟡 巡检器产出与执行器能力矩阵严重错配

| | |
| --- | --- |
| 现状 | `daily_issue_router` 产出 6 类问题，但 `agent_task_executor` 只自动修 **3 类**（`title_too_long` / `meta_description_too_short` / `ai_forbidden_word`）。另外 **5 类在代码里硬编码为 `need_manual`**：`content_placeholder` / `image_missing_alt` / `title_too_short` / `draft_leak` / `social_zero_engagement` |
| 优化动作 | 与 B4 合并决策：要么收窄 router 产出（只产出可自动修的），要么扩展 executor 能力矩阵 |
| 台账 id | `AUDIT-OPS-002` |

## B4 · 🔴 追踪闭环空转 18 天——分配了等于没分配

| | |
| --- | --- |
| 现状 | `reports/daily_issues/execution_log.json`：自 **2026-09-04 起执行数千轮**，累计 `resolved ≈ 0`，累计 `failed = 0`，所有 issue 终态为 `need_manual` / `manual_review` |
| 例证 | `task_2026-09-14_seo` 在 09-14 一天内被执行约 **30 轮**，轮次结果恒为 `resolved=2 / need_manual=5`，无任何推进 |
| 后果 | 调度器每 30 分钟唤醒 → agent 读同一个不可修的问题 → 写回 `need_manual` → 下一轮重复。台账持续膨胀但无一项前进 |
| 方案 | **A（推荐，低风险）**：收窄 router 产出，只路由 executor 能自动修的类型，其余走人工工单而非 agent 任务<br>**B**：扩展 executor 能力矩阵——**必须先关闭 B1/B2（误报源），否则会自动执行一批错误修改**<br>两方案都需：给 `need_manual` 增加**终态语义**（超 N 轮未解决 → 标 `blocked` 并升级，而不是继续重复派单） |
| 优化动作 | 需你决策方案。无论选哪个，都要给 `need_manual` 加终态 |
| 台账 id | `AUDIT-OPS-002` |

---

# C 层：报告指出的业务侧优化项（4 项）

含 3 项报告自身已暴露的，与 1 项**报告完全没看到**的新缺陷。

## C1 · 🔴 线上 7 个孤儿页 + 4 个裸 URL 桩页（日报未覆盖）

| | |
| --- | --- |
| 现状 | `public/posts/` 共 **67 页**，其中 **7 个（10.4%）在 `content/` 全树中找不到已发布源文件**：6 个真孤儿 + 1 个仅由 `_draft/` 草稿支撑 |
| 孤儿清单 | `/posts/best-travel-insurance-china/`、`/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/`、`/posts/is-china-safe-for-tourists-2026-honest-assessment/`、`/posts/is-china-safe-for-tourists-2026-honest-safety-assessment/`、`/posts/2026-05-26-is-china-safe-for-tourists-2026-honest-assessment/`、`/posts/2026-05-27-how-to-survive-chinese-train-station/`、`/posts/transportation-guide-guide/` |
| 附加缺陷 | **4 个页面 `<title>` 是一个裸 URL**（`2026-09-01-...-monthly-update` / `how-to-survive-chinese-train-station` / `is-china-safe-for-tourists-2026-honest-assessment` / `transportation-guide-guide`）——重定向桩，无真实标题 |
| 附加缺陷 | `is-china-safe-for-tourists-2026-honest-assessment` 与 `...-honest-safety-assessment` **同时在线**，同主题两 URL 分流权重 |
| 根因 | `hugo.toml` **未设置 `cleanDestinationDir`**（默认 `false`），Hugo 构建**从不删除**已下线页面 |
| 危害 | 5 个带正常标题的孤儿页持续被 Google 收录抓取，**很可能正在获得排名与曝光而团队以为已下线**。`best-travel-insurance-china` 是商业意图强的页面，可能仍在产生佣金，也可能完全失联 |
| 优化动作 | ① `hugo.toml` 加 `cleanDestinationDir = true`——⚠️ **这是构建行为变更，必须先 dry-run 构建并 diff `public/` 确认不误删静态资源**；② 先在 GSC 查这 7 个 URL 的实际曝光/点击/排名**量化仍在获得的流量**；③ 逐页决策：仍在获得流量 → 恢复内容源文件或 301；已下线 → `_redirects` 加 301 或 404；④ 重建后确认页面数 67→60、裸 URL 标题 4→0 |
| 高危 | ✅ 涉及线上内容与构建行为，**须先向你说明影响并等确认** |
| 约束 | `_redirects` 规则目标须写**无扩展名且精确匹配（不带 `*`）**，不得新增 `/ops/ops-center` 规则 |
| 台账 id | `AUDIT-OPS-001`（阻塞 `AUDIT-SEO-002` / `AUDIT-SEO-003` / `AUDIT-CT-002`） |

## C2 · 🔴 实验登记表三方矛盾——日报据其把 DRIVE-001 升级为待办 #1

| | |
| --- | --- |
| 现状 | 日报状态源 `static/experiments.json`，`updated_at = 2026-09-06`（**已 15 天未更新**），且与另两份登记表矛盾 |
| 冲突① | **DRIVE-001**：日报显示 `PLANNED` 并升级为「今日高优先级待办 #1 🔴」；`docs/AI_CONTEXT.md` 记 `RUNNING（start 2026-08-16，ACTIVE）`；`reports/revenue/EXPERIMENT_COMPARISON.csv` 记 `observation_days=1, INSUFFICIENT_SAMPLE, data_source=CACHED` |
| 冲突② | **REV002**：日报显示 `PLANNED`；`reports/revenue/REV002_EXPERIMENT_REGISTRY.csv` 记 `status=RETIRED, decision=RETIRED_INVALID_INSTRUMENT`——**已退役，不应显示为待启动** |
| 冲突③ | **REV001**：日报显示 `PLANNED, 0d`；`AI_CONTEXT.md` 记 `RUNNING（start 2026-08-16）`——若为真则是 **36 天 0 样本**，属埋点失效而非未启动 |
| 危害 | 若 Drive 实际在跑，日报的 #1 待办是**假警报**，浪费排查精力；若确实未部署，则另两份登记表需修正。**两种情况下日报都没给出正确判断依据**——它把一份 15 天前、且自相矛盾的文件当事实输出并升级告警 |
| 代码侧 | `feishu_daily_report.py:894-895` 只检测**单向**漂移（快照 RUNNING 实为幻影）；**反向漂移**（experiments.json 陈旧 → 在跑实验显示 PLANNED）无处理 |
| 优化动作 | ① **现场核实** DRIVE-001：查线上页面 HTML 中 Travelpayouts 横幅是否真存在，及 GA4 `banner_click` 是否有数据；② 统一三方：更新 experiments.json 的 status 与 `updated_at`，把 REV002 的 RETIRED 同步过去，修正 AI_CONTEXT.md 的不实记录；③ 判定 REV001 若真在跑 36 天 0 样本，确认 `affiliate_click` 埋点是否存在（与 C3 共用结论）；④ 建立**单一事实源**约定：明确 experiments.json 为唯一源、AI_CONTEXT.md 只引用不复制状态，并加 `updated_at` 陈旧校验 |
| 台账 id | `AUDIT-RV-001`（阻塞 `AUDIT-CT-001` 的联盟位部分） |

## C3 · 🟠 佣金归因链不可验证——tracking 覆盖达标但 12 次点击 0 归因

| | |
| --- | --- |
| 现状 | 覆盖率 **211/211** 已达标（已重跑 `affiliate_link_audit.audit()` 确认真实）。但链路另一端断裂：`tp_inits` 持续「未上报」，**12 次点击全部 0 归因**（0 订单 / $0.00） |
| 问题 | 「链接带 tracking」只是必要条件，实际归因链是否工作**无法从现有数据判断** |
| 优化动作 | ① 人工登录 Travelpayouts 核实是否真有 12 次点击记录（本机无法访问）；② 排查 `tp_inits` 为何持续未上报（采集缺失 / 字段映射错 / API 无此字段）；③ 确认 `affiliate_click` GA4 事件埋点是否存在——**若缺失，所有实验的 `primary_metric` 都不可测，这比单个实验状态更根本** |
| 保留的正确设计 | NordVPN/AffiliatesCN 未接入自动化，日报已标注「合计佣金 $0.00 仅为接入渠道下限，不是全量」——**保留** |
| 台账 id | `AUDIT-RV-002` |

## C4 · 🟢 两条真实 SEO 问题（唯一通过真伪核验的站点告警）

| | |
| --- | --- |
| ① | `content/posts/2026-06-22-shanghai-beyond-the-bund-hidden-neighborhoods-and-local-culture.md` meta description **166 字符**超阈值 165 → 压缩到 ≤160 字符。已在 `execution_log` 中反复派发 16+ 次从未推进 |
| ② | `content/success.md` title `'Payment Successful!'` **19 字符** < `TITLE_MIN=20` —— 数值真实，但**阈值对支付成功页不适用**，建议按页型豁免而非改写标题 |
| 台账 id | `AUDIT-SEO-001` |
| ⚠️ | 其余 7 条告警（3 条 title_too_short + 2 条 content_placeholder + 1 条 draft_leak）**已核验为误报或定性错误，台账中已关闭**，不要再派单 |

---

# D 层：日报覆盖缺口（4 项）

这些是日报**应该监控但没有监控**的项。D 层不是修 bug，是补盲区。

## D1 · 孤儿页监控缺失

日报 QA 只扫 `content/`，**永远看不到 `public/` 里的孤儿**。C1 因此存在 18 天无人察觉。→ 增加 `public/` vs `content/` 源文件的对账扫描（见 A5）。

## D2 · 登记表新鲜度监控缺失

`static/experiments.json` 15 天未更新，`gsc_*_28d` 37 天未刷新，都无任何告警。→ 给所有「登记表/缓存快照」类数据源加 `updated_at` 阈值校验，超过 N 天在日报显式标注陈旧。

## D3 · 双扫描器交叉校验缺失

A3 的两套扫描器互不校验，才会出现互斥结论。→ 收敛为单一实现（A3），或至少增加交叉比对：两扫描器结论不一致时告警。

## D4 · 数据源真实性交叉校验缺失

日报自述「GA4 来源未证实：脚本查数值 ID、hugo.toml 写 measurement ID，无交叉验证」。此缺陷仍成立。→ 增加 GA4 property ID 与快照中实际查询 ID 的一致性校验；`tp_inits` / `gsc_*_28d` 等「未上报/陈旧」字段应有显式数据质量标签而非默认值。

---

# 已关闭（不要重复优化）

以下 6 项经核验为**误报或定性错误**，已在台账中关闭。**不要再据此改内容**：

| 项 | 判定 | 为什么 |
| --- | --- | --- |
| `contact.md` content_placeholder | 误报 | 3 处全是 HTML `<input placeholder="...">` 表单属性 |
| `search.md` content_placeholder | 误报 | 文件带 BOM → front-matter 解析失配 → 整文件当正文 → 命中 YAML 键 `placeholder:` |
| `xian-terracotta-army` title_too_short（报 2 字符） | 误报 | 真实 40 字符，撇号截断到 `"Xi"` |
| `china-high-speed-rail` title_too_short（报 17） | 误报 | 真实 58 字符，截断到 `"How To Ride China"` |
| `foodies-guide-to-china` title_too_short（报 6） | 误报 | 真实 44 字符，截断到 `"Foodie"` |
| `2026-07-22-cultural-etiquette-guide.md` draft_leak（high） | 定性错误，降为 low | slug 是 `cultural-etiquette-guide-aussie-kiwi`，线上无此路径；已发布页由 07-21 正式版支撑。**不是泄露**，是草稿放错目录（已重映射到 `AUDIT-CT-002`） |

---

# 执行顺序建议

```
第 1 步  C2 现场核实 DRIVE-001      ← 先确认告警真伪，避免继续浪费 #1 优先级
第 2 步  C1 孤儿页逐页决策          ← 高危，需你确认后执行（先 dry-run diff）
第 3 步  B1 + B2 消除误报源         ← 阻塞 B4 方案 B；不修则自动修复会执行错误改动
第 4 步  B4 决策追踪闭环方案 A/B     ← 否则下面所有新工单会像前 18 天一样空转
第 5 步  A1 + A2 + A4 报表口径      ← 让日报自己可信
第 6 步  C3 佣金归因链              ← 需登录 Travelpayouts 后台
第 7 步  A6 + A7 + C4 内容/SEO      ← 低风险收尾
第 8 步  D1-D4 补监控盲区           ← 防止同类问题再次存在 18 天
```

**关键路径**：B1/B2 必须在 B4 方案 B 之前完成；C2 必须在任何 CTA/联盟位变更前完成。

---

# 设计偏差与边界

1. **未修改任何文件、未执行任何修复、未 commit**。所有 19 项均为登记与指派状态。C1 的 `cleanDestinationDir` 属构建行为变更，需先 dry-run 构建并 diff `public/`。
2. **上游真实值未验证**。本次只验证「日报数字与其引用的本地数据文件一致」，未验证「本地文件与第三方后台一致」。GA4 / GSC / MailerLite / Travelpayouts 均需后台访问。日报自述的两条数据源局限（GA4 property 未交叉验证、NordVPN 未接入）**仍成立**。
3. **本报告只覆盖 2026-09-21 这一份日报**。未回溯历史日报是否重复出现同类错标（例如 OKR 7 天窗口错标是否每天都发生）。若要确认系统性，需抽样比对历史日报。
4. **孤儿页判定有近似**：Hugo 的 slug 解析按「显式 `slug:` 优先，否则取文件名去日期前缀」近似实现，与官方规则可能有细微差异。6 个真孤儿页已逐个核对 slug 在 `content/` 全树中确实不存在任何源文件，结论稳健。
5. **`pass2` 不构成缺陷**：初查曾怀疑新文章 `audit_status: pass2` 偏低，实测 64 篇中 pass2=26 / pass4=7 / 无该字段=31，pass2 是已发布文章多数态，已撤回该判断。同理 C4-② 的 19 字符标题是数值真实但阈值不适用，不建议改写。
6. **A 层与 B 层有重叠**：A3/A4 与 B1/B2 的修复若一起做，改动面会重叠。建议按第 3、5 步顺序分两批做，便于回归验证。
