# P1-GROWTH-28 — SEO CTR Growth Pilot

- 生成日期: 2026-08-19
- 状态: **P1-GROWTH-28 = PASS**
- 未 commit / 未 push
- 变更范围: 3 个内容文件，仅 title / description front matter

---

## 1. 目标页面与基线（source: GSC raw_pages_90d，报告日期 2026-08-19；GSC 缓存快照基线 2026-08-16）

| # | Page | content_id | Impressions | Clicks | CTR% | Avg Pos | Fetch/Source date |
|---|---|---|---|---|---|---|---|
| 1 | China Travel Guide: August 2026 Updates & Visa Rules | cbt-80ac63165adb | 52 | 0 | 0.0 | 11.4 | 2026-08-19 (GSC cached 2026-08-16) |
| 2 | China Photography Guide | cbt-bfeaa5ca9007 | 51 | 0 | 0.0 | 20.9 | 2026-08-19 (GSC cached 2026-08-16) |
| 3 | Yunnan Travel Guide | cbt-23c31fe5b281 | 40 | 0 | 0.0 | 20.7 | 2026-08-19 (GSC cached 2026-08-16) |

低样本提示：三页 clicks 均为 0、CTR=0%，属于 LOW_DATA_WARNING 范围；**观察期 < 28 天或 clicks < 20 前禁止判定 WIN/LOSE**。

---

## 2. 逐页分析与最小改动

### 2.1 China Travel Guide: August 2026 Updates & Visa Rules（cbt-80ac63165adb）

- Title/query 对齐：当前 title 主关键词顺序合理，但 "Updates & Visa Rules" 对 "china visa rules 2026 / china travel august 2026" 类查询的显式匹配弱；月份与 "China Travel Guide" 未相邻。
- Description/intent 对齐：主意图为"最新签证规则+月度更新"；原描述用 "visa changes"，与高频查询词 "visa rules" 不完全一致；"payment updates" 重复 "updates"。
- 优化后 title：`China Travel Guide August 2026: Latest Visa Rules & Updates`
- 优化后 description：`August 2026 China travel updates: latest visa rules, crowd forecasts, payment changes, scam alerts, and seasonal picks.`（≤155 chars）
- 改动：仅 title / description 两行 front matter。

### 2.2 China Photography Guide（cbt-bfeaa5ca9007）

- Title/query 对齐：原 title "Best Spots & Tips" 覆盖面窄；页面实际覆盖 gear、lighting、composition 与 12 个目的地最佳机位，与 "china photography spots / gear" 查询匹配不足。
- Description/intent 对齐：原描述以 "gear, lighting, composition" 开头，弱化了最高频意图 "best photo locations"；专业权威信号（"from a pro"）被置于句尾。
- 优化后 title：`China Photography Guide: Best Spots, Gear & Tips from a China Pro`
- 优化后 description：`Best photo locations across 12 Chinese destinations, plus gear, lighting and composition tips from a pro who's shot China for 5+ years.`（≤155 chars）
- 改动：仅 title / description 两行 front matter。

### 2.3 Yunnan Travel Guide（cbt-23c31fe5b281）

- Title/query 对齐：页面核心价值是 7 日行程 + 元阳梯田 + 大理/丽江古城；原 title 未突出 itinerary，年份信号缺失。
- Description/intent 对齐：主意图为行程规划（"yunnan itinerary 7 days / plan yunnan"）；原描述以 "Yunnan in 7 days" 陈述式开头，弱引导；页面含 transport tips 未体现。
- 优化后 title：`Yunnan Travel Guide 2026: 7-Day Itinerary, Rice Terraces & Ancient Towns`
- 优化后 description：`Plan Yunnan in 7 days: Kunming, Yuanyang rice terraces, Dali, Lijiang and Jade Dragon Snow Mountain, with real prices and transport tips.`（≤155 chars）
- 改动：仅 title / description 两行 front matter。

**保护确认**：URL / slug / canonicalURL / content_id / H1 / 正文 / 联盟链接 / UTM / GA4 / REV001 / REV002 / DRIVE-001 均未改动。

---

## 3. 实验注册

| experiment_id | Page | start_date | primary_metric | secondary_metrics | minimum_observation_days | review_gate |
|---|---|---|---|---|---|---|
| GROWTH28-CTR-001 | August 2026 Monthly Update | 2026-08-19 | CTR | impressions, average_position | 28 | 2026-09-16 |
| GROWTH28-CTR-002 | China Photography Guide | 2026-08-19 | CTR | impressions, average_position | 28 | 2026-09-16 |
| GROWTH28-CTR-003 | Yunnan Travel Guide | 2026-08-19 | CTR | impressions, average_position | 28 | 2026-09-16 |

基线见第 1 节；评审门槛：观察 ≥ 28 天 且 clicks ≥ 20，否则维持 RUNNING / INSUFFICIENT_SAMPLE，不宣布胜负。

---

## 4. 验证结果

| 检查项 | 结果 |
|---|---|
| `pytest tests/ -q` | **626 passed / 0 failed / 0 skipped**（含密钥扫描 test_no_hardcoded_secrets.py / test_secret_name_contract.py） |
| `content_id_audit.py audit --strict` | **PASS**（60/60，0 缺失 / 0 重复 / 0 格式错误） |
| `hugo --gc --minify` | **PASS**（377 pages） |
| meta audit（audit_meta_descriptions.py --audit） | 3 个目标页无问题（P0 duplicate = 0 → PASS）；2 个过长描述为其他文章的既有问题，未改动 |
| internal link audit（audit_internal_links.py --audit） | **PASS**（589 links，404/301/malformed = 0） |
| secret scan | PASS（pytest 内 secret 测试通过） |
| Node affiliate check（check_affiliate_links.cjs） | **5/6 OK**（affiliatescn / trip.com / booking.com / safetywing）；Airalo `https://www.airalo.com/` TCP 连接超时（DNS 正常解析 108.160.163.116，Travelpayouts 跳转链 emrldtp 返回 301 正常）→ 归类 TIMEOUT / PARTNER_BLOCKED，需人工浏览器确认，**非链接失效证据** |

### 4.1 护栏测试同步（6 个失败 → 0）

全量 pytest 首轮 6 个失败均为护栏测试的硬编码内容白名单未包含 P1-GROWTH-28 授权文件（photography / yunnan 为新增，monthly-update 已在 P1-GROWTH-25 白名单内）。已同步 5 个测试文件：

- `tests/test_brand_identity_p2.py`（GROWTH28_AUTHORIZED + 2 处白名单）
- `tests/test_brand_legacy_pilot.py`
- `tests/test_growth07_content_differentiation.py`
- `tests/test_growth21_payment_cluster.py`
- `tests/test_travelpayouts_drive.py`

同步后全量 pytest 626 passed / 0 failed / 0 skipped。

---

## 5. 变更文件清单

- `content/posts/2026-08-01-chinabound-travel-guide-2026-08-monthly-update.md`（title + description）
- `content/posts/2026-08-01-china-photography-guide-capturing-the-wonders-of-the-middle-kingdom.md`（title + description）
- `content/posts/2026-07-05-yunnan-adventure-rice-terraces-ancient-towns-and-ethnic-minorities-guide.md`（title + description）
- 护栏测试 5 个文件（授权白名单同步）
- 本报告 + `reports/seo/P1_GROWTH_28_EXPERIMENT_REGISTRY.csv`

## 6. 下一轮行动

- 2026-09-16 前不评估 CTR 结果；届时对比 GSC 28d 窗口。
- 人工浏览器确认 airalo.com 可达性（本网络到 Airalo 80/443 TCP 层均超时，其余 5 个联盟目标正常）。
- 若 CTR 改善且样本充分，再评估扩展到其他 T1 页面。

---

**最终状态: P1-GROWTH-28 = PASS**
