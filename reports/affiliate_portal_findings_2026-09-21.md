# 联盟 Tracking 参数实证与落地报告

日期：2026-09-21
来源：用户 Chrome 浏览器远程调试（CDP :9222）实测，非推测
账户：fys2388@gmail.com · Travelpayouts ID **730795**

---

## 1. 实测方法与边界

通过 Chrome `--remote-debugging-port=9222` 连上用户真实登录态，用 Playwright
`connect_over_cdp` 逐个访问联盟后台，读取 cookie / 页面结构 / 生成链接。
全程只读 + 一次正常的「Generate link」操作，未创建账号、未提交申请、未改仓库配置
（唯一写入是本文第 5 节记录的 `hugo.toml` 一处，经用户确认）。

---

## 2. 登录态实测结果

| 平台 | 后台入口 | Cookie 状态 | 结论 |
|---|---|---|---|
| **Travelpayouts** | app.travelpayouts.com | 37 个，含 `access_token` / `refresh_token` / `tp_session` / `daily_login` / `auth_method` / `marker` | ✅ **已登录** |
| NordVPN | affiliates.nordvpn.com | **0** | ❌ 未登录（与用户所述「通的可用」不符） |
| Airalo Partner | partners.airalo.com | **0** | ❌ 未登录 |
| Impact | app.impact.com | **0** | ❌ 未登录（用户报告申请被拒，一致） |

说明：Travelpayouts 首次 `ctx.cookies()` 只截断打印前 12 个名字，把认证 cookie
挡住了，误判为未登录。改用 `get_cookies(url=...)` 全量拉取后确认已登录。

---

## 3. 关键发现：报告的两处事实错误已更正

### 3.1 eSIM 并非「不在 Travelpayouts 网络内」—— 已更正 ✅

`reports/commerce_fix_2026-09-21.md` 与 `hugo.toml` 注释原判定：
> 「eSIM 不在 Travelpayouts 覆盖范围内，无法用已入驻联盟替代；
> 唯一解是去 Airalo Partner 拿新的 referral 码。」

**实测推翻**：Travelpayouts Programs 页显示 **26 个已开通程序**，其中三个 eSIM 程序
全部带「Generate links」按钮：

| 程序 | ID | 佣金 | Cookie |
|---|---|---|---|
| **Airalo** | 541 | 12% | 30 天 |
| Yesim | 224 | **18%** | **90 天** |
| GigSky | 636 | 20% | 30 天 |

Airalo 自 2023-02-02 起就已入驻，只是之前没人去后台生成短链。
报告里建议的「登录 partners.airalo.com 申请 referral code」**完全不需要做**。

### 3.2 Trip.com 不是「token 格式问题」，是程序准入未通过 —— 已更正 ✅

原判定：「Travelpayouts 理论上覆盖 Trip.com，但深链需后台生成 token」。

**实测**：打开 `programs/121/about`（Trip.com），页面明确显示：

> **25 programs are currently unavailable for Chinaboundtravel**
> Your website doesn't currently have enough traffic. Submit for review once it has
> stable monthly traffic for at least three consecutive months.

即 Trip.com（以及另外 24 个程序）在本站点**未开通**。原仓库里猜的
`https://trip.tpo.li/trains?marker=730795` 返回 404，表面看是格式错误，
**真实原因是程序本身没准入**——生成 token 的入口根本不存在。

### 3.3 顺带确认：Klook 归因一直是真的 ✅

生成页「Recently added」列表显示：
`https://klook.tpo.li/vrPkmS2v` · June 17, 05:58 am · **730795**
与 `hugo.toml` 现值完全一致，说明 Klook 的联盟归因一直在正常运作。

---

## 4. 已生成的链接与验证

**Airalo（程序 541）** — 生成于 2026-09-21 06:29 UTC+8：

```
https://airalo.tpo.li/39yPity6
```

跳转链实测（`Invoke-WebRequest -MaximumRedirection 0`）：

```
302 → https://airalo.pxf.io/c/1209822/1310283/15608
        ?sharedID=730795_&subId1=419b3d0f8a7448a5b0c9f578c-730795
        &u=https%3A%2F%2Fwww.airalo.com%2F
```

- `sharedID=730795_` 已烧入 ✅
- `u=` 正确编码目的地 ✅
- 走 CJ Affiliate（px.f.io）正规联盟网络 ✅

对照现有 Klook 链接同模式验证：
`302 → https://affiliate.klook.com/redirect?aid=api|13694|...-730795|pid|730795` ✅

### Airalo 佣金限制（后台原文）

- **App 内购买不计佣金** —— 仅桌面 + 移动网页计佣
- **自己购买不计佣金**
- 订单在次月 8 日前标记为 Paid（如 3/2 购买 → 4/8 前标记）

---

## 5. 已落地的改动（经用户确认）

用户选择：写入 Airalo 链接；Trip.com 保留 GAP 标记。

`hugo.toml` `[params.affiliate]`：

```
改前  esim = "https://www.airalo.com/"          # ⛔ GAP：渲染 156 处
改后  esim = "https://airalo.tpo.li/39yPity6"   # ✅ TRACKED 2026-09-21
```

同步更正的注释：
1. 覆盖状态表：esim 从 ⛔ GAP 移入 ✅ TRACKED
2. 「❌ Travelpayouts 覆盖不到」段删除 esim 条目，改为标注原判定错误
3. trip 条目改为记录真实原因（程序未开通 + 需 3 个月稳定流量）
4. esim 注释补齐生成时间、跳转链验证、App 内不计佣金、Yesim/GigSky 备选

备份（已移出仓库，避免被 `git add -A` 扫入）：
- `E:\AI\dulizhan\backups\hugo-toml-2026-09-21\hugo.toml.before-esim-edit`
- `E:\AI\dulizhan\backups\hugo-toml-2026-09-21\hugo.toml.before-trip-comment`

TOML 语法已校验通过（`tomllib.load`）。

---

## 6. 遗留

1. **Trip.com 未开通** —— 需站点月流量稳定满 3 个月后，在 Travelpayouts
   后台 Trip.com 程序页点「Submit for review」，通过后再去 Links 生成 token。
   开通前保持裸 URL + ⛔ GAP 标记，不伪装已修复。
   备选：Kiwitaxi（程序 1，9-11% / 30 天）已开通可生成链接。

2. **World Nomads / Allianz** —— Travelpayouts 无对应保险产品，仍是真 GAP。
   Impact 申请被拒（app.impact.com 0 cookie，与用户报告一致）。

3. **NordVPN** —— 后台 0 cookie，需重新登录才能核实现有
   `get.affiliatescn.net aff_id=150687` 的当前状态。这是第三方转售渠道，
   不是官方直连，佣金与结算周期需在 NordVPN 官方后台确认。

4. **Balance $0 + 未设 payout method** —— Travelpayouts 后台提示
   "To receive payouts, set your payout method"。**即使联盟链接全部生效，
   不设收款方式也拿不到钱**。这是上线前的硬前置。

5. **Klook 短链 2027-07-24 到期** —— 需续期，已在 hugo.toml 记录。

6. **测试状态**：`test_travelpayouts_drive.py::test_no_content_or_affiliate_files_touched`
   与 `test_brand_identity_p2.py::test_affiliate_urls_unchanged` 现报
   `值变: ['esim']`。这是**正确行为**——t16 修的 URL 值比较精确抓到了本次合法改动，
   断言对比的是工作区 vs HEAD，需 commit 后才归零。
   `test_canonical_unchanged` 仍是 pre-existing（HEAD 50ed17d1 把 hello@ 改成 joran@）。

---

## 7. 设计偏差

1. **原判定「eSIM 不在 Travelpayouts 网络内」是错的** —— 本文 §3.1 更正。
   根因：之前只看了 `partners.airalo.com`（Airalo 直连渠道），
   没查 Travelpayouts 的 SIM-cards 分类。
2. **原判定 Trip.com「需后台生成 token」不完整** —— 实际是程序准入未通过，
   token 生成入口不存在。修正后行动项从「生成 token」变成「等流量满 3 个月再申请」。
3. 未修改任何 content/posts/、未触碰 ops-center.html、未执行 git 写操作。
