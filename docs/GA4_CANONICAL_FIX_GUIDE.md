# GA4 canonical 修复操作指南

> 背景：2026-09-20 人工核对 GA4 控制台发现同一账号下有两个数据流网址
> 完全相同的属性。仓库已按**方案 A** 统一为 `538482322` / `G-GECBME3YVJ`
> （commit `3c982aa6`）。本文是剩下的手工步骤。

## 账号

| 项 | 值 |
|---|---|
| Google 账号 | `fys2388@gmail.com`（Joran Fan） |
| GA4 账号 | `fys2388` / 账号 ID `192133217` |
| **canonical 属性** | `ChinaBound Travel` → `chinaboundtravel` / **`538482322`** / 衡量 ID **`G-GECBME3YVJ`** |
| 重复属性 | ~~`541752321`~~ 衡量 ID `G-P6BH500VBK` —— **已归档**（2026-09-20 19:55，最终删除 2026-10-25） |

canonical 数据流：名称 `chinaboundtravel`，数据流 ID `14917784829`，
网址 **`https://www.chinaboundtravel.com`**（已改，2026-09-20）。

---

## 第 1 步 ✅ 本地 `.env`（已完成）

```
GA4_PROPERTY_ID=538482322
```

已改。`.env` 被 `.gitignore` 排除，不进仓库 —— 这是正确做法。

---

## 第 2 步 ✅ GitHub Secrets（已完成 2026-09-20 12:07 UTC）

1. 打开 <https://github.com/fys2388/chinaboundtravel/settings/secrets/actions>
2. 找到 `GA4_PROPERTY_ID`
3. Edit → 值改为 **`538482322`** → Save
4. 顺带确认这三个 secret 还在（缺了会让 GA4/GSC 采集整体失效）：
   `GA4_API_KEY`、`GA4_SERVICE_ACCOUNT_JSON`、`GSC_SERVICE_ACCOUNT_JSON`

> 这步不做，CI 上的日报仍读旧属性，仓库改动只修了本地。

---

## 第 3 步 ✅ 归档重复属性 `541752321`（已完成 2026-09-20 19:55）

1. <https://analytics.google.com/analytics/web/#/a192133217/admin/properties>
2. 账号选择器（左上角）→ 选中 `ChinaBound Travel 541752321`
3. 左侧「媒体资源」→「媒体资源详细信息」
4. 右上角「更多操作 ⋮」→ **删除** → 确认删除
   （或先「归档」，回收站保留 30 天可恢复 —— 推荐归档）

> 归档不影响 `538482322` 的数据。归档后 Google 端那个多余 destination
> 的目标属性消失，第 4 步的 destination 清理会更容易判断。

---

## 第 4 步 ✅ 数据流网址改为带 www（已完成 2026-09-20）

线上站点是 `https://www.chinaboundtravel.com`，但两个数据流都登记的是
无 www 的 `https://chinaboundtravel.com`。这会影响跨域归属和内部流量过滤。

**canonical 属性（必做）**

1. <https://analytics.google.com/analytics/web/#/p538482322/admin/data-streams>
2. 点开 `chinaboundtravel https://chinaboundtravel.com`
3. 点「修改网站数据流设置」
4. 数据流网址改为 **`https://www.chinaboundtravel.com`** → 保存

> 如果第 3 步已归档 `541752321`，这一步只做 canonical 这一个。
> 若尚未归档，`541752321` 那个数据流（ID `15078079911`）不用改，反正要删。

---

## 第 5 步 删掉 Google Tag 里的多余 destination

`gtag.js?id=G-GECBME3YVJ` 的载荷里有 **两个** `__dest_ga` 配置：
`G-GECBME3YVJ`（tag_id 1）和 `G-P6BH500VBK`（tag_id 7）。
每个事件被同时发到两个属性。要删掉 `G-P6BH500VBK` 那个。

**先确认容器归属** —— `fys2388@gmail.com` 名下
[<https://tagmanager.google.com/>](https://tagmanager.google.com/) 的
账号列表是**空的**，所以这个容器在别的 Google 账号下。

排查路径：

1. 回忆站点最初是谁搭的、用的哪个 Google 账号（可能是组织账号或旧个人号）
2. 换账号登录 GTM，看是否有容器 ID（形如 `GTM-XXXXXXX`）
3. 找到后 → 容器 → 标签 → 找到那个 Google 标签（Google Analytics 配置标签）
   → 「目标配置（Targeting）」或「设置 → 配置」→ 删掉第二个配置
   （配置 ID 为 7 的那个，衡量 ID `G-P6BH500VBK`）→ 发布

> 如果第 3 步已经归档了 `541752321`，这个 destination 会变成失效目标，
> 但仍应删掉 —— 否则每次事件还在发一个无效请求（2x 开销与配额）。

**找不到容器怎么办**：临时兜底是在仓库里改用直连 gtag（不走 GTM），
即 `hugo.toml` 只保留 `G-GECBME3YVJ`、删掉所有其他 ID 的 config 行。
但这等于放弃 GTM 的集中管理，且当前站点 HTML 里本来就只有 1 个 ID
（`G-GECBME3YVJ`），重复来自 `gtag.js` 载荷的服务端配置 —— 所以
**直连 gtag 也照样会被那份载荷里的两个 destination 影响**，必须找到容器。

---

## 验证清单

| 检查项 | 预期 | 命令 / 位置 |
|---|---|---|
| `.env` | ✅ `GA4_PROPERTY_ID=538482322` | `Select-String -Path .env '^GA4_PROPERTY_ID='` |
| GitHub Secrets | ✅ `2026-09-20T12:07:07Z` | `gh secret list --repo fys2388/chinaboundtravel` |
| posture 一致性 | ✅ `config_mismatch: false` | `reports/quality/analytics_posture.json` |
| 载荷只剩 1 个 destination | ⏳ 仍 `destination_count: 2` | 同上，第 5 步完成后重跑 site_health_agent |
| 重复属性 | ✅ 已归档，最终删除 2026-10-25 | GA4 账号 → 回收站可见 `ChinaBound Travel` |
| 数据流网址 | ✅ `https://www.chinaboundtravel.com` | GA4 → 数据流详情页 |

重跑校验（第 5 步完成后）：

```powershell
cd E:\AI\dulizhan\travel-blog
$env:PYTHONIOENCODING='utf-8'
python -c "import sys; sys.path.insert(0,'scripts'); from site_health_agent import check_analytics_measurement_ids; print(check_analytics_measurement_ids())"
```

`destination_count` 变为 `1` 后，KPI 里的 `DUPLICATE_DESTINATION` 状态会
自动清除，`users_28d` 等 4 个流量 KPI 恢复为 `OK`。

---

## 仓库侧已经固化的防线

- `config/analytics_canonical.json` —— canonical 声明落盘（含决策与依据）
- `site_health_agent.check_analytics_measurement_ids()` 第 3 层 —— 校验
  `hugo.toml` TrackingID / `GA4_PROPERTY_ID` / canonical 声明三方一致性，
  不一致报 `analytics_config_inconsistency`（critical）
- `reporting_kpi_engine` —— `config_mismatch` 与 `duplicate_destinations`
  任一为真，GA4 来源 KPI 都标 `DUPLICATE_DESTINATION`
- `tests/test_analytics_canonical_config.py` 12 项，含能力边界断言：
  该校验**只能**发现仓库内自相矛盾，**不能**核实两套编号是否属同一属性
  （核实需要 GA4 Admin API，当前服务账号 401）
