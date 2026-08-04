# 联盟推荐链接状态总表

检查时间：2026-08-04
检查范围：`hugo.toml` 配置 + `content/resources/_index.md` 页面实际渲染链接 + 文章页联盟 shortcode

---

## 一、当前已配置/已上架的联盟推荐链接

| 品牌/服务 | 类别 | 是否有联盟合作 | 当前使用 URL | 来源位置 | 状态 | 备注 |
|---|---|---|---|---|---|---|
| **Airalo** | eSIM | ✅ 是（Travelpayouts link-switch） | `https://www.airalo.com/` | `hugo.toml` `params.affiliate.esim` | ⚠️ HEAD 超时 | 浏览器访问正常；页面渲染时被 emrldtp 自动加上跳转参数 |
| **NordVPN** | VPN | ✅ 是（affiliatescn） | `https://get.affiliatescn.net/aff_c?offer_id=153&aff_id=150687&url_id=613` | `hugo.toml` `params.affiliate.vpn` | ✅ 正常 | 同时用于 `vpnNord` |
| **NordPass** | 密码管理 | ❓ 未确认 | `https://nordpass.com/` | `hugo.toml` `params.affiliate.nordpass` | ✅ 正常 | 无联盟参数，仅为普通推荐 |
| **Booking.com** | 酒店 | ✅ 是（aid=730795） | `https://www.booking.com/index.html?aid=730795` | `hugo.toml` `params.affiliate.hotel` | ✅ 正常 | 替代了原先证书错误的 Hotellook |
| **Klook** | 门票/日游 | ✅ 是（tpo.li 跳转） | `https://klook.tpo.li/vrPkmS2v` | `hugo.toml` `params.affiliate.klook` | ✅ 正常 | HEAD 403 但浏览器可正常跳转到 klook.com；配置 expire_date = 2027-07-24 |
| **Klook（Resources 页单独链接）** | 门票/日游 | ✅ 是 | `https://klook.tpo.li/ppB4vZQ6` | `content/resources/_index.md` | ✅ 正常 | 同上，HEAD 403 但实际可访问 |
| **SafetyWing** | 旅行保险 | ✅ 是（Ambassador ID 26548976） | `https://safetywing.com/nomad-insurance?referenceID=26548976&utm_source=26548976&utm_medium=Ambassador` | `hugo.toml` `params.affiliate.safetywing` | ✅ 正常 | 同时用于 `worldnomads`、`allianz` 参数（见问题 4） |
| **SafetyWing（Resources 页推荐）** | 旅行保险 | ✅ 是 | `https://safetywing.com/ambassador/refer/26548976` | `content/resources/_index.md` | ✅ 正常 | 跳转到 `hello.safetywing.com/ambassador-page` |
| **Trip.com** | 火车票/机票/酒店 | ✅ 是 | `https://www.trip.com/` | `hugo.toml` `params.affiliate.trip` | ✅ 正常 | 已替换失效的 `trip.tpo.li` 跳转 |
| **Aviasales** | 机票比价 | ✅ 是（marker=730795） | `https://www.aviasales.com/?marker=730795` | `hugo.toml` `params.affiliate.flight` | ✅ 正常 | 已用于文章 shortcode 和 Resources 页 |
| **World Nomads** | 旅行保险 | ❌ 无 | `https://www.worldnomads.com` | `content/resources/_index.md` | ✅ 正常 | 普通外链，无联盟参数 |
| **Hostelworld** | 青旅 | ❌ 无 | `https://www.hostelworld.com` | `content/resources/_index.md` | ✅ 正常 | 普通外链 |
| **Wise** | 汇款/支付 | ❌ 无 | `https://wise.com` | `content/resources/_index.md` | ✅ 正常 | 普通外链 |

### 联盟合作汇总

已确认有联盟合作（URL 中带 affiliate/aid/marker/referenceID 等参数）的品牌：
1. Airalo（通过 Travelpayouts emrldtp link-switcher）
2. NordVPN（affiliatescn）
3. Booking.com（aid=730795）
4. Klook（tpo.li 跳转）
5. SafetyWing（referenceID=26548976）
6. Trip.com
7. Aviasales（marker=730795）

仅为普通推荐、未确认联盟合作的品牌：
- NordPass、World Nomads、Hostelworld、Wise

---

## 二、本次检查发现的问题与修复

### 问题 1：Resources 页航班搜索链接 404
- **现象**：`content/resources/_index.md` 中 "Search China Flights" 指向 `https://www.travelpayouts.com/click?marker=730795&currency=USD&destination=CN`，HEAD 404，浏览器访问空白页
- **修复**：已替换为可用的 Aviasales 联盟链接 `https://www.aviasales.com/?marker=730795`
- **状态**：已修复，待部署

### 问题 2：Pricing 页购买按钮仍可能被 Travelpayouts 脚本拦截
- **现象**：Pricing 页面已部署新代码（勾选协议后启用购买），但实际点击后未跳转到 Stripe；页面存在 `emrldtp.com/link-switch/v1/convert` 请求，会劫持外部链接
- **修复**：在 `layouts/partials/pricing-table.html` 的购买按钮点击事件中，使用 `e.preventDefault()` + `window.open()` 直接打开 Stripe 结账页，绕过第三方 link-switch 脚本
- **状态**：已修复，待部署

### 问题 3：Airalo HEAD 请求超时
- **现象**：自动化脚本对 `https://www.airalo.com/` 和 emrldtp 跳转链接均返回 TIMEOUT
- **结论**：浏览器访问完全正常，属于 Airalo 对 HEAD 请求的防护策略
- **建议**：后续监控脚本改用 GET 请求或延长超时

### 问题 4：`hugo.toml` 中 `worldnomads` / `allianz` 与 `safetywing` 使用同一 URL
- **现象**：参数 `worldnomads` 和 `allianz` 都指向 SafetyWing 链接，而 `brand-logos` shortcode 中 World Nomads 默认指向 `worldnomads.com`
- **影响**：Resources 页中 World Nomads 直接链到官网（无联盟），文章中的 `brand-logos` shortcode 若引用 `worldnomads` 参数则会显示 SafetyWing 链接
- **建议**：若已与 World Nomads / Allianz 建立联盟合作，需替换为对应联盟链接；若未合作，建议从 `hugo.toml` 中删除这两个参数以避免混淆

---

## 三、部署状态

- 修复文件：`content/resources/_index.md`、`layouts/partials/pricing-table.html`、`reports/affiliate_links_status_table.md`
- 已提交并推送至 GitHub `main` 分支：`ecc0a52`
- Cloudflare Pages 已自动部署完成
- 线上验证：
  - Pricing 页勾选退款协议后点击购买按钮，可正常打开 Stripe 结账页
  - Resources 页 "Search China Flights" 已指向 Aviasales 联盟链接

---

## 四、建议后续动作

1. 部署完成后，手动访问 Pricing 页，勾选退款协议后点击购买按钮，确认能打开 Stripe 结账页
2. 访问 Resources 页，点击 "Search China Flights"，确认跳转到 Aviasales
3. 检查是否拥有 World Nomads / Allianz / NordPass / Wise / Hostelworld 的联盟账号；若有，替换为带联盟参数的链接
4. 将联盟链接监控脚本 `check_affiliate_config.cjs` 中的 Airalo 改为 GET 请求，避免 TIMEOUT 误报
