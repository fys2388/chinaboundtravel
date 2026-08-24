# P1-GROWTH-27R — Test Environment Repair & Verification

- 生成日期: 2026-08-19
- 工作目录: `E:\AI\dulizhan\travel-blog`
- 状态: **P1-GROWTH-27R = PASS**
- 未 commit / 未 push

---

## 1. 环境故障诊断

| 项目 | 结果 |
|---|---|
| 故障现象 | `python -m pytest tests/ -q` 无法运行（命令指向 WindowsApps stub，报"系统无法访问此文件"） |
| 根因 | 系统 PATH 中的 `python` 是损坏的 WindowsApps 占位程序（`C:\Users\神魂之人\AppData\Local\Microsoft\WindowsApps\python.exe`），不是真实 Python 解释器 |
| 正确环境 | **Accio 预装 Python**：`C:\Users\神魂之人\AppData\Roaming\Accio\pre-install\python\python.exe`（Python 3.12.2，pytest 8.2.0） |
| 证据 | 仓库根目录 `pytest_tests.log` 记录同一解释器路径与版本 |

## 2. 环境恢复

- 未安装任何全局包。
- 使用项目既有 Accio 预装 Python 直接运行 pytest，无需恢复步骤。
- 命令模板：`& 'C:\Users\神魂之人\AppData\Roaming\Accio\pre-install\python\python.exe' -m pytest tests/ -q`

## 3. 全量回归结果

| 检查 | 结果 |
|---|---|
| `pytest tests/ -q` | **626 passed, 0 failed, 0 skipped** |
| `scripts/content_id_audit.py audit --strict` | **PASS**（60 posts / 60 content_id，0 缺失 / 0 重复 / 0 格式错误） |
| `hugo --gc --minify` | **PASS**（377 pages，0 错误） |

### 3.1 测试护栏同步（3 个文件，均为授权改动）

首轮全量 pytest 出现 3 个失败，均为护栏测试未同步 P1-GROWTH-27 已授权改动，而非实现缺陷。已同步：

1. `tests/test_growth21_payment_cluster.py` — 白名单增加 `content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md`。
2. `tests/test_growth07_content_differentiation.py` — allowed_layouts 增加 `layouts/shortcodes/ab-cta.html`。
3. `tests/test_growth07b_technical_seo.py` — 渲染对比前归一化 `cta_id` / `experiment_id` 新增归因参数。

### 3.2 发现并修复的真实模板缺陷

渲染验证发现 `layouts/shortcodes/affiliate-mid-cta.html` 中 `data-affiliate-partner` / `data-affiliate-placement` 被渲染成**链接内文字**而非 HTML 属性，且存在重复行。已修复为单一正确属性行：

```html
<a href="{{ $url }}" class="affiliate-link" target="_blank" rel="nofollow sponsored"
   data-affiliate-partner="{{ $partner }}" data-affiliate-placement="{{ $placement }}"
   data-cta-id="{{ $ctaId }}" data-experiment-id="{{ $experimentId }}">
```

修复后重新 `hugo --gc --minify` 并复验渲染页通过（见下）。修复仅限模板属性结构，未改 CTA 文案、链接、布局或归因语义。

## 4. REV001 / REV002 归因验证（渲染后页面）

### REV001 — Food Delivery（Airalo / REV001）

- 页面: `public/posts/chinese-food-delivery-meituan-eleme-guide/index.html`
- content_id: `cbt-e464169c4991` ✅
- mid-CTA 属性: `partner=esim`、`placement=food-delivery-mid-content`、`cta_id=rev001-food-delivery-esim`、`experiment_id=REV001` ✅
- 事件: `affiliate_impression` ✅ / `affiliate_click` ✅ / `affiliate_outbound` ✅
- JS 字段: `page_path=window.location.pathname`、`cta_id=e.getAttribute("data-cta-id")`、`experiment_id=e.getAttribute("data-experiment-id")` ✅
- 属性泄漏文字: 无 ✅

### REV002 — Transportation（Trip.com / REV002）

- 页面: `public/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/index.html`
- content_id: `cbt-17c6738ffb32` ✅
- mid-CTA 属性: `partner=trip`、`placement=transportation-train-tickets-mid`、`cta_id=rev002-transportation-trip`、`experiment_id=REV002` ✅
- 事件: `affiliate_impression` ✅ / `affiliate_click` ✅ / `affiliate_outbound` ✅
- JS 字段: `page_path=window.location.pathname`、`cta_id=e.getAttribute("data-cta-id")`、`experiment_id=e.getAttribute("data-experiment-id")` ✅
- 属性泄漏文字: 无 ✅

结论：两个实验页的 content_id + page_path + partner + placement + cta_id + experiment_id 六字段均可在页面级可靠识别；三个归因事件均存在。

## 5. 联盟 / Node 回归

- pytest 侧联盟相关测试全部通过（包含在 626 passed 内）。
- `scripts/check_affiliate_links.cjs`（Node）：本次沙箱网络全断，6 个唯一联盟 URL 探活全部返回 `EACCES` / `ERROR`（如 `connect EACCES 66.220.149.18:443`），为**环境网络限制导致的假阴性**，非链接损坏证据。需在具备网络的 CI/本机环境复跑确认真实链接健康度。
- 未修改任何 affiliate URL、UTM、CTA 文案或位置。

## 6. 变更清单（本任务）

- `layouts/shortcodes/affiliate-mid-cta.html` — 修复重复/泄漏的属性行（模板缺陷修复，最小改动）。
- `tests/test_growth21_payment_cluster.py` — 护栏白名单同步。
- `tests/test_growth07_content_differentiation.py` — allowed_layouts 同步。
- `tests/test_growth07b_technical_seo.py` — 归因参数归一化同步。
- `reports/P1_GROWTH_27R_TEST_ENVIRONMENT_REPAIR.md` — 本报告。

未修改：content/posts、affiliate URL、REV001/REV002 CTA 文案与位置、GA4 schema、GSC、Drive、Stripe、Buffer。

## 7. 剩余事项

- 在联网环境复跑 `scripts/check_affiliate_links.cjs` 与 `check_affiliate_config.cjs`，确认 6 个联盟目标真实可达。
- 模板修复后已重跑全量 pytest 确认无回归（626 passed）。

---

**最终状态: P1-GROWTH-27R = PASS**
