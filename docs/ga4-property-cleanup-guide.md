# GA4 属性清理操作清单

> **本文档目标**：把 `config/analytics_canonical.json#pending_actions` 里的 5 项待完成动作展开为可执行的 Google 控制台操作清单，供人工在浏览器里逐项核对。
>
> **决策时间**：2026-09-20（人工上 GA4 控制台核对，账号 `fys2388` / 账号 ID `192133217`）
>
> **canonical 属性**：`538482322` / `G-GECBME3YVJ`
> **重复属性**：`541752321` / `G-P6BH500VBK`
>
> **相关文档**：
> - `config/analytics_canonical.json` —— 决策记录与 pending_actions 声明
> - `docs/GA4_CANONICAL_FIX_GUIDE.md` —— 首版操作指南（2026-09-20 记录各步实际完成时间）
> - `reports/quality/analytics_posture.json` —— 机器可读的诊断姿态
> - `scripts/site_health_agent.py` L1198–L1392 —— `_check_analytics_config_consistency` 与 `check_analytics_measurement_ids`

---

## 背景

2026-09-20 人工上 GA4 控制台核对账号 `fys2388`（账号 ID `192133217`）下的媒体资源时，发现：

1. **同一个 Google 账号下挂了两个数据流网址完全相同的属性**：
   - `ChinaBound Travel 538482322` → 衡量 ID `G-GECBME3YVJ`，28 天活跃用户 **234**
   - `ChinaBound Travel 541752321` → 衡量 ID `G-P6BH500VBK`，7 天 55（换算 28 天约 **246**）
   - 两个数据流网址都登记为 `https://chinaboundtravel.com`（线上站点实际是 `https://www.chinaboundtravel.com`）
2. **每个事件被送到两个属性**：线上页面 HTML 只加载了 `gtag.js?id=G-GECBME3YVJ`，但 gtag.js 载荷的服务端配置里包含 **两个 `__dest_ga` destinationId**（tag_id 1 → `G-GECBME3YVJ`；tag_id 7 → `G-P6BH500VBK`），每次 `page_view` 同时 POST 到两个 tid。
3. **根因在 Google Tag Manager 控制台**：gtag.js 载荷里的多 destination 配置由 GTM 服务端生成，改仓库代码修不了 —— 仓库里没有第二个 gtag，重复完全来自 Google 侧的 tag 配置。
4. **仓库里两套编号互不校验**：`hugo.toml` 写 measurement ID（`G-GECBME3YVJ`），所有脚本查数值 property ID（`GA4_PROPERTY_ID`）。旧配置默认 `GA4_PROPERTY_ID=541752321` —— 即一直在读那个重复属性。

详见 `config/analytics_canonical.json` 的 `rationale` 字段与 `site_health_agent.py` L1273–L1347 的注释。

---

## 当前状态

从 `reports/quality/analytics_posture.json`（`checked_at: 2026-09-23T08:33:36+00:00`）提取：

| 字段 | 值 | 含义 |
|---|---|---|
| `duplicate_destinations` | `true` | gtag.js 载荷里仍配 2 个 destination → **KPI 权威地位未证实** |
| `contaminated` | `true` | 同上（旧字段名，读取方两者都认） |
| `config_mismatch` | `false` | 仓库内 `hugo.toml` / `.env` / canonical 声明三方自洽 |
| `destination_count` | `2` | `G-GECBME3YVJ` + `G-P6BH500VBK` |
| `html_measurement_ids` | `["G-GECBME3YVJ"]` | 页面 HTML 里只有 1 个 gtag ID —— 重复不来自仓库 |
| `canonical_config.env_property_id` | `""` | 最近一次 `site_health_agent` 运行时未加载 `.env`（该 Python 子进程没通过 dotenv 载入，与 `.env` 内容本身无关） |

受影响的 KPI：`users_28d` / `sessions_28d` / `pageviews_28d` / `engagement_rate_28d` —— 数值本身没被双计，但无法证明读的是 canonical 属性，所以 `reporting_kpi_engine` 会给它们打上 `CONTAMINATED_SOURCE`。

> **关键判断**：`duplicate_destinations=true` 的根因在 Google 侧（GTM 容器里的 Google Tag 配了多个 destinationId），仓库侧改代码无法修 —— 见 `site_health_agent.py` L1343–L1346。这也是 `config/site_health_whitelist.json#WL-003` 把该 issue 标为 `external_blocked` 的原因。

---

## 待执行动作

### 动作 1：更新本地 `.env` 的 `GA4_PROPERTY_ID`

- **状态**：✅ 已完成（2026-09-20，见 `docs/GA4_CANONICAL_FIX_GUIDE.md` § 第 1 步）
- **当前值**：`GA4_PROPERTY_ID=538482322`（依据 `docs/GA4_CANONICAL_FIX_GUIDE.md`；受项目 AGENTS.md 安全规则约束，本文档不直接读取 `.env` 内容）
- **目标值**：`538482322`（canonical）

**验证方法**（在本地执行，不 commit）：

```powershell
cd E:\AI\dulizhan\travel-blog
Select-String -Path .env '^GA4_PROPERTY_ID='
```

预期输出：`GA4_PROPERTY_ID=538482322`

**兜底检查**：所有脚本的默认 fallback 已经改为 `538482322`，即使 `.env` 缺失也不会读到旧属性：

```python
# scripts/feishu_daily_report.py L141, feishu_weekly_report.py L63, 等
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "538482322")
```

---

### 动作 2：更新 GitHub Secrets 的 `GA4_PROPERTY_ID`

- **状态**：✅ 已完成（2026-09-20 12:07 UTC，见 `docs/GA4_CANONICAL_FIX_GUIDE.md` § 第 2 步）
- **目标值**：`538482322`

**具体点击路径**（供回归核对，如果未来需要再次修改）：

1. 打开仓库：<https://github.com/fys2388/chinaboundtravel>
2. 左侧栏 → **Settings**（右上角齿轮图标）
3. 左侧菜单展开 **Secrets and variables** → **Actions**
4. 在「Repository secrets」列表找到 `GA4_PROPERTY_ID`（若不存在则点 **New repository secret**）
5. **Name**：`GA4_PROPERTY_ID`（保持不变）
6. **Secret**：填入 `538482322`
7. **Save secret**
8. **顺带确认这三个 secret 仍在**（缺任何一个都会让 CI 上的 GA4 采集失效）：
   - `GA4_API_KEY`
   - `GA4_SERVICE_ACCOUNT_JSON`
   - `GSC_SERVICE_ACCOUNT_JSON`

**CLI 复核**（可选，需已装 GitHub CLI 且已 `gh auth login`）：

```powershell
gh secret list --repo fys2388/chinaboundtravel | Select-String 'GA4_PROPERTY_ID'
```

预期输出含 `GA4_PROPERTY_ID  2026-09-20T12:07:07Z` 或更晚。

---

### 动作 3：在 Google Tag Manager 里删掉 `G-P6BH500VBK` destination

- **状态**：✅ 已完成（2026-10-02，通过 Google 代码管理器 UI 操作）
- **操作方式**：将 `G-P6BH500VBK` 分配到新建的独立代码 `chinaboundtravel-duplicate`，主代码 `chinaboundtravel` 只保留 `G-GECBME3YVJ`
- **结果**：主代码不再向 `G-P6BH500VBK` 发送数据，双目的地污染已消除

**历史卡点记录**（2026-09-20 曾卡住）：

1. 用 `fys2388@gmail.com` 登录 <https://tagmanager.google.com/>
2. 顶部账号选择器 → 展开 → 显示「**账号列表为空**」（2026-09-20 人工核对）
3. 也就是说，`G-P6BH500VBK` 这个 destination 所属的 GTM 容器**不在这个 Google 账号下**，无法直接改

**具体操作路径（2026-10-02 实际执行）**：

1. 打开 <https://tagmanager.google.com/> → 切换到 **Google 代码** 标签
2. 找到代码 `chinaboundtravel`（代码 ID：G-GECBME3YVJ, GT-NGSXZL7C, G-P6BH500VBK, GT-PL9QDZJS）
3. 点击代码进入「管理 Google 代码」编辑界面
4. 在「代码 ID」区域，点击 `G-P6BH500VBK` 旁的「**将"G-P6BH500VBK"分配给新的 Google 代码**」
5. 填写新代码名称 `chinaboundtravel-duplicate`，选择「使用默认配置」和「请勿复制用户」
6. 点击「查看所做选择」→「保存更改」
7. 回到编辑界面，在「目标账号」表格中找到 `G-P6BH500VBK` 行，点击「**移除目标账号**」
8. 选择「选择现有代码」→ 选中 `chinaboundtravel-duplicate`
9. 点击「保存」
10. 验证：主代码的「目标账号」表格只剩 `G-GECBME3YVJ` 一行

**历史排查路径（2026-09-20 记录，现已无效）**：

- **路径 A：找容器所有者** —— 2026-10-02 确认容器实际在 `fys2388@gmail.com` 账号下（Google 代码标签页可见），原「账号列表为空」可能是当时看的是 GTM 账号而非 Google 代码
- **路径 B/C/D**：不再需要

**发布后验证**：

1. 打开线上首页 <https://www.chinaboundtravel.com/>
2. 打开开发者工具 → Network → 筛选 `ga` 或 `gtag`
3. 刷新页面 → 找到 `gtag/js?id=G-GECBME3YVJ` 的响应
4. 在响应里搜索 `__dest_ga`：应只剩 1 个 destination（`G-GECBME3YVJ`），不应再出现 `G-P6BH500VBK`

---

### 动作 4：归档或删除重复属性 `541752321`

- **状态**：✅ 已完成（归档 2026-09-20 19:55；最终删除 2026-10-25，见 `docs/GA4_CANONICAL_FIX_GUIDE.md` § 第 3 步）

**具体点击路径**（已执行，供回归核对）：

1. 打开 <https://analytics.google.com/analytics/web/#/a192133217/admin/properties>
2. 左上角账号选择器 → 切换到 `ChinaBound Travel 541752321`
3. 左侧菜单 → **管理** → **媒体资源设置** → **媒体资源详细信息**
4. 右上角 **更多操作 ⋮** → **删除**（推荐先「归档」，回收站保留 30 天可恢复）
5. 二次确认弹窗 → **确认删除**

**归档前必须确认**（历史检查清单）：

```bash
# 在仓库里搜索是否还有任何脚本硬编码引用 541752321
grep -rn "541752321" . --include="*.py" --include="*.json" --include="*.toml" --include="*.yml" --include="*.md"
```

预期：`tests/test_analytics_canonical_config.py`（测试用例里作为反例）和文档里的历史引用；不应有活跃的生产代码引用。

> ⚠️ **重要**：这个动作**不能**替代动作 3。归档属性 `541752321` 之后，`G-P6BH500VBK` 这个 measurement ID 在 Google 侧变成一个**失效目标**，但 gtag.js 载荷里仍然带着它 —— 每次事件还是会发一个无效请求（2x 开销与配额，且 Google Analytics 会记录这条无效流量直到 GTM 配置修改并发布）。

---

### 动作 5：把数据流网址改为 `https://www.chinaboundtravel.com`

- **状态**：✅ 已完成（2026-09-20，见 `docs/GA4_CANONICAL_FIX_GUIDE.md` § 第 4 步）

**具体点击路径**（已执行，供回归核对）：

1. 打开 <https://analytics.google.com/analytics/web/#/p538482322/admin/data-streams>
2. 左侧菜单 → **管理** → **数据流**
3. 找到 `chinaboundtravel` 这个 Web 数据流（数据流 ID `14917784829`）→ 点击
4. 页面底部「网站数据流设置」→ **修改网站数据流设置**
5. **数据流网址** 输入框：把 `https://chinaboundtravel.com` 改为 `https://www.chinaboundtravel.com`
6. **保存**

> 属性 `541752321` 已在动作 4 归档，其对应的数据流（ID `15078079911`）不用改，反正随属性一起归档。

**原因**：线上站点是 `https://www.chinaboundtravel.com`（裸域 301 到 www）。数据流登记为裸域会导致跨域归属识别、内部流量过滤、Search Console 跨域验证等边缘情况失效。

---

## 验证方法

每个动作完成后，重新跑：

```powershell
cd E:\AI\dulizhan\travel-blog
$env:PYTHONIOENCODING='utf-8'
python scripts/site_health_agent.py
```

或直接调单点：

```powershell
python -c "import sys; sys.path.insert(0,'scripts'); from site_health_agent import check_analytics_measurement_ids; print(check_analytics_measurement_ids())"
```

**判定标准**：`reports/quality/analytics_posture.json` 里：

- `duplicate_destinations: false` **且**
- `contaminated: false` **且**
- `destination_count: 1`

**当前阻塞**：只有动作 3 完成，这两个字段才会翻转为 `false`。动作 1/2/4/5 都已在 2026-09-20 完成，但 `duplicate_destinations` 至今仍为 `true` —— 因为它取决于动作 3 的 GTM 服务端配置。

**回归测试**：

```powershell
cd E:\AI\dulizhan\travel-blog
python -m pytest tests/test_analytics_canonical_config.py -v
```

预期 12 项测试全过（含「`_check_analytics_config_consistency` 只能发现仓库内自相矛盾、不能核实 property ↔ measurement 映射」的能力边界断言）。

---

## 回滚

| 动作 | 可回滚性 | 回滚方法 |
|---|---|---|
| 动作 1：`.env` `GA4_PROPERTY_ID` | ✅ 完全可回滚 | 编辑 `.env` 改回 `541752321`，保存（`.env` 不进 git，无提交可 revert） |
| 动作 2：GitHub Secrets | ✅ 完全可回滚 | GitHub Settings → Secrets and variables → Actions → `GA4_PROPERTY_ID` → Edit → 值改回 `541752321` → Save。Secret 值本身无历史版本，改一次立即生效 |
| 动作 3：GTM destination 删除 | ✅ 可回滚 | GTM → 版本 → 展开历史版本列表 → 找到删除前的版本 → **恢复此版本** → 发布。GTM 版本保留 90 天 |
| 动作 4：归档属性 `541752321` | ⚠️ **部分可回滚** | 归档后 30 天内可从 GA4 → 管理 → **回收站** 恢复；30 天后**永久删除、不可恢复**。恢复后其数据流 ID `15078079911` 也一起复活 |
| 动作 5：数据流网址 | ✅ 完全可回滚 | 回 GA4 → 数据流详情页 → 修改网站数据流设置 → 数据流网址改回裸域 → 保存 |

**⚠️ 特别提醒**：

- 动作 4（归档属性）在 2026-09-20 19:55 已执行，若现在还未超过 30 天，可从 GA4 回收站恢复；否则**永久失去**。这是**唯一不可逆**的动作。
- 动作 4 的恢复不会自动撤销动作 3（GTM destination 仍在），也不会自动更新动作 1/2/5 —— 五个动作是独立可回滚的。
- 回滚任何动作后**必须**重跑 `site_health_agent.py`，让 `reports/quality/analytics_posture.json` 反映新状态，否则 `reporting_kpi_engine` 会拿着过时数据判断 KPI 是否 contaminated。

---

## 附录

### A. canonical 决策的完整 rationale

引用 `config/analytics_canonical.json`（决策时间 2026-09-20）：

```json
{
  "canonical_property_id": "538482322",
  "canonical_measurement_id": "G-GECBME3YVJ",
  "decision": "方案 A —— 以 hugo.toml 声明的 measurement ID 为准",
  "decided_at": "2026-09-20",
  "confirmed_by": "GA4 控制台人工核对（账号 fys2388 / 账号ID 192133217）",
  "duplicate_property_ids": ["541752321"],
  "duplicate_measurement_ids": ["G-P6BH500VBK"],
  "rationale": [
    "账号下 3 个属性：538482322 衡量 ID = G-GECBME3YVJ，541752321 衡量 ID = G-P6BH500VBK，",
    "两者数据流网址完全相同（https://chinaboundtravel.com），是同站点的重复属性。",
    "hugo.toml 与线上 gtag 配置都指向 G-GECBME3YVJ，所以它为准。",
    "旧版脚本默认 GA4_PROPERTY_ID=541752321 —— 即一直在读重复属性。",
    "28 天活跃用户：538482322 = 234，541752321 = 7 天 55（换算 28 天约 246）。"
  ],
  "pending_actions": [
    "本地 .env 的 GA4_PROPERTY_ID 改为 538482322",
    "GitHub Secrets 的 GA4_PROPERTY_ID 改为 538482322",
    "在 Google Tag Manager 删掉 G-P6BH500VBK 这个 destination（该容器不在 fys2388@gmail.com 账号下，需另找持有账号）",
    "归档或删除重复属性 541752321",
    "把两个数据流网址从 https://chinaboundtravel.com 改成 https://www.chinaboundtravel.com"
  ]
}
```

**关键 rationale 解读**：选择方案 A（以 `G-GECBME3YVJ` 为准）而非方案 B（切到 `G-P6BH500VBK`），因为：

- `hugo.toml` 的 `TrackingID` 已经写了 `G-GECBME3YVJ`，改动面最小
- 线上 `gtag.js` 载荷里 tag_id 1 就是 `G-GECBME3YVJ`（主标签），tag_id 7 才是 `G-P6BH500VBK`（次要/追加标签）
- 两个属性的 28 天活跃用户数值接近（234 vs ~246），说明历史上两属性都在跑，无强信号偏向某一方；因此选择与仓库声明一致的一方

### B. 相关代码位置

- **`scripts/site_health_agent.py` L1198–L1220**：`_load_analytics_canonical_config()` —— 读 `config/analytics_canonical.json`，缺失不报错
- **`scripts/site_health_agent.py` L1223–L1234**：`_read_hugo_measurement_id()` —— 从 `hugo.toml` 正则抓 `TrackingID`
- **`scripts/site_health_agent.py` L1237–L1270**：`_check_analytics_config_consistency()` —— 三方一致性校验（canonical / hugo / `GA4_PROPERTY_ID`），返回 `(mismatch: bool, detail: dict)`
- **`scripts/site_health_agent.py` L1273–L1392**：`check_analytics_measurement_ids()` —— 三层检测：(1) HTML 里出现几个 ID；(2) gtag.js 载荷里几个 destination；(3) 仓库内配置自洽性；写出 `reports/quality/analytics_posture.json`
- **`scripts/reporting_kpi_engine.py` L280 起**：读 posture 文件，若 `duplicate_destinations` 或 `config_mismatch` 为 true，把 GA4 来源的 4 个流量 KPI 标 `CONTAMINATED_SOURCE`
- **`tests/test_analytics_canonical_config.py`**：12 项 pytest，含能力边界断言（该校验**只能**发现仓库内自相矛盾，**不能**核实 property ↔ measurement 是否属同一属性）

### C. 能力边界（重要）

- **仓库侧能查的**：`hugo.toml` 的 `TrackingID` 与 `GA4_PROPERTY_ID` 环境值是否自洽
- **仓库侧查不了的**：property ID 与 measurement ID 是否属于同一个属性 —— 这需要 GA4 Admin API（`analyticsdata.googleapis.com` 之外），而当前服务账号只有 Data API 权限，Admin API 会返回 401
- **所以**：`config/analytics_canonical.json` 里 `canonical_property_id` 与 `canonical_measurement_id` 的映射关系是**人工上控制台核对后固化**的，无法由仓库自动化验证。这也是为什么本文档强调「动作 4 归档属性前，用 grep 确认没有脚本硬编码引用 541752321」

### D. 豁免清单

- **`config/site_health_whitelist.json#WL-003`**：把 `type: multiple_analytics_destinations` 标为 `external_blocked`，理由正是「duplicate destination 不在 fys2388@gmail.com 账号下，需另找持有账号」。这条豁免在动作 3 完成后应删除，让 site_health_agent 重新报告。

### E. 术语对照

| 术语 | 说明 |
|---|---|
| **property ID** | GA4 属性的数值 ID，如 `538482322`。脚本查数值走这个 |
| **measurement ID** | GA4 属性的度量 ID，形如 `G-XXXXXXXXXX`。页面 HTML 里的 gtag 用这个 |
| **data stream** | 属性下面的采集通道，一个 Web 属性至少 1 个数据流 |
| **destination** | gtag.js 载荷里的 `__dest_ga` 条目，可有多条 —— 每条把事件送到一个 measurement ID |
| **canonical** | 决策后选定的「权威」属性，其他重复属性应归档或删除 |
| **contaminated** | 旧字段名，与 `duplicate_destinations` 同义；`reporting_kpi_engine` 两者都认 |
