# ChinaBound Travel - 联盟 Partner API 接入操作指南

> 原则：只使用真实 API 数据，禁止模拟数据。无凭证或调用失败时明确标记 `REVENUE_NOT_AVAILABLE`。

## 已接通状态总览

| Partner | API 状态 | 数据状态 | 操作 |
|---------|----------|----------|------|
| Travelpayouts | ✅ 已接通 | ✅ 有真实数据 | 无需操作 |
| Partnerize | ✅ API 连通 | ⚠️ 0 campaign | 需登录后台加入 campaign |
| NordVPN | ❌ 无直接 API | ❌ 无数据 | 需在 Impact.com 获取 API 凭证 |
| Klook | ❌ 无凭证 | ❌ | 需申请 API 访问权限 |
| Booking.com | ❌ 无凭证 | ❌ | 需申请 Booking.com Affiliate API |
| Airalo | ❌ 无凭证 | ❌ | 需申请 Airalo Partner API |
| Aviasales | ❌ 无凭证 | ❌ | 属 Travelpayouts 旗下，可用 Travelpayouts API |
| SafetyWing | ❌ 无凭证 | ❌ | 需申请 SafetyWing API |
| Trip.com | ❌ 无凭证 | ❌ | 需申请 Trip.com Affiliate API |
| Allianz | ❌ 无凭证 | ❌ | 需通过联盟网络申请 |
| World Nomads | ❌ 无凭证 | ❌ | 需通过联盟网络申请 |

---

## 第 1 点：Partnerize 后台操作（需用户手动完成）

### 1.1 确认账户类型

Partnerize 有两种账户视角：
- **Brand/Advertiser（广告主）**：管理自己的联盟计划，查看推广者带来的转化
- **Partner/Publisher（发布商/推广者）**：作为推广者加入品牌的联盟计划，获取佣金

**当前 API 测试结果**：`/v3/brand/campaigns` 返回 200 但 `data: []`，说明凭证是 **Brand 视角**，但账户下没有创建任何 campaign。

### 1.2 操作步骤

1. **登录 Partnerize 后台**：https://www.partnerize.com/
2. **确认账户类型**：
   - 登录后看左上角菜单，如果显示 "Brand" 则是广告主账户
   - 如果显示 "Partner" 则是发布商账户
3. **如果是 Brand 账户**：
   - 进入 **Campaigns** 菜单
   - 点击 **Create Campaign** 创建联盟计划
   - 或检查是否有已创建但未激活的 campaign
4. **如果是 Partner 账户**：
   - 进入 **Find Brands** 或 **Marketplace**
   - 搜索相关品牌（如旅游、保险、VPN 类）
   - 申请加入这些品牌的联盟计划
   - 等待品牌方审核通过
5. **获取 campaign_id**：
   - campaign 创建/加入后，在 campaign 详情页 URL 中找到 campaign_id
   - 格式通常为 `cam-xxxxxxxx` 或纯数字

### 1.3 验证

campaign 配置完成后，运行：
```bash
python scripts/real_data_pull_engine.py --partnerize
```
预期输出：`获取到 N 个 campaign`，并自动拉取每个 campaign 的 conversions 数据。

---

## 第 2 点：NordVPN / Impact.com API 接入（需用户手动获取凭证）

### 2.1 背景

NordVPN 的联盟计划通过 **Impact.com** 管理，没有直接的公开 API。需要通过 Impact.com 的 API 获取转化和收入数据。

### 2.2 获取 Impact API 凭证

1. **登录 Impact.com**：https://app.impact.com/
2. 进入 **Settings** → **API Access**
3. 记录以下凭证：
   - **Account SID**（账户 ID，格式 `ACxxxxxx`）
   - **Auth Token**（认证令牌）
4. 如果没有 API Access 选项，联系 Impact 支持开通 API 权限

### 2.3 配置凭证

在 `.env` 文件中添加：
```env
IMPACT_ACCOUNT_SID=ACxxxxxxxxxxxx
IMPACT_AUTH_TOKEN=xxxxxxxxxxxx
IMPACT_NORDVPN_CAMPAIGN_ID=xxxxxx
```

### 2.4 API 接入代码框架

已在 `scripts/real_data_pull_engine.py` 中预留 Impact API 接入框架。凭证配置完成后，取消注释并运行：
```bash
python scripts/real_data_pull_engine.py --impact
```

Impact API 端点参考：
- 获取转化：`https://api.impact.com/Advertisers/{AccountSID}/Actions`
- 获取点击：`https://api.impact.com/Advertisers/{AccountSID}/Clicks`
- 获取campaign：`https://api.impact.com/Advertisers/{AccountSID}/Campaigns`

---

## 第 3 点：其他 8 个 Partner API 检查清单

### 3.1 Klook

- **联盟平台**：Klook Affiliate Program（https://affiliate.klook.com/）
- **API 可用性**：Klook 提供 Affiliate API，需在联盟后台申请
- **申请步骤**：
  1. 登录 Klook Affiliate 后台
  2. 进入 **Tools** → **API**
  3. 申请 API Key 和 API Secret
  4. 记录 API 端点文档
- **凭证配置**：
  ```env
  KLOOK_API_KEY=xxxxxxxx
  KLOOK_API_SECRET=xxxxxxxx
  ```

### 3.2 Booking.com

- **联盟平台**：Booking.com Affiliate Partner Program
- **API 可用性**：Booking.com 提供 Affiliate API，但需单独申请且有流量门槛
- **申请步骤**：
  1. 登录 https://affiliate.booking.com/
  2. 进入 **Account** → **API Access**
  3. 检查是否满足 API 访问条件（通常需要月点击量达标）
  4. 如不满足，可使用 Booking.com 的搜索框/链接生成器作为替代
- **替代方案**：使用 Travelpayouts 的 Booking.com 数据（Travelpayouts 已接通）

### 3.3 Airalo

- **联盟平台**：Airalo Partner Program（https://www.airalo.com/partners）
- **API 可用性**：Airalo 提供 Partner API，需联系合作伙伴经理申请
- **申请步骤**：
  1. 登录 Airalo Partner 后台
  2. 查找 **API Documentation** 或 **Developer** 菜单
  3. 如无 API 选项，发送邮件至 partners@airalo.com 申请 API 访问
  4. 获取 Client ID 和 Client Secret
- **凭证配置**：
  ```env
  AIRALO_CLIENT_ID=xxxxxxxx
  AIRALO_CLIENT_SECRET=xxxxxxxx
  ```

### 3.4 Aviasales

- **联盟平台**：Travelpayouts（Aviasales 是 Travelpayouts 旗下品牌）
- **API 可用性**：✅ 已通过 Travelpayouts API 接通
- **操作**：无需额外操作，Aviasales 数据包含在 Travelpayouts API 返回中

### 3.5 SafetyWing

- **联盟平台**：SafetyWing Affiliate Program（https://safetywing.com/affiliate/）
- **API 可用性**：SafetyWing 联盟通过 PartnerStack 或自定义平台管理，API 需申请
- **申请步骤**：
  1. 登录 SafetyWing 联盟后台
  2. 查找 **API** 或 **Developer** 选项
  3. 如无，联系联盟经理申请 API 访问
  4. 获取 API Key
- **凭证配置**：
  ```env
  SAFETYWING_API_KEY=xxxxxxxx
  ```

### 3.6 Trip.com

- **联盟平台**：Trip.com Affiliate Program（https://affiliate.trip.com/）
- **API 可用性**：Trip.com 提供 Affiliate API，需在后台申请
- **申请步骤**：
  1. 登录 Trip.com Affiliate 后台
  2. 进入 **Tools** → **API**
  3. 申请 API 访问权限
  4. 获取 App ID 和 App Secret
- **凭证配置**：
  ```env
  TRIP_APP_ID=xxxxxxxx
  TRIP_APP_SECRET=xxxxxxxx
  ```

### 3.7 Allianz

- **联盟平台**：Allianz 通常通过联盟网络（如 Partnerize、Impact、CJ）管理
- **API 可用性**：取决于所在联盟网络的 API 能力
- **操作**：
  1. 确认 Allianz 联盟计划在哪个网络上
  2. 如果在 Partnerize 上 → 已接通（需加入 campaign）
  3. 如果在 Impact 上 → 参考 NordVPN Impact API 接入
  4. 如果在其他网络 → 申请该网络的 API 凭证

### 3.8 World Nomads

- **联盟平台**：World Nomads 通常通过 CJ Affiliate 或自定义平台管理
- **API 可用性**：CJ Affiliate 提供 REST API，需申请
- **操作**：
  1. 确认 World Nomads 联盟计划在哪个网络上
  2. 如果在 CJ 上 → 申请 CJ REST API 凭证（https://developers.cj.com/）
  3. 获取 Personal Access Token
  4. 配置凭证：
     ```env
     CJ_API_TOKEN=xxxxxxxx
     ```

---

## 通用接入流程

对于每个新 Partner，接入流程统一为：

1. **确认联盟平台**：该 Partner 在哪个联盟网络上（自建/Partnerize/Impact/CJ/其他）
2. **申请 API 凭证**：登录联盟后台，申请 API 访问权限，获取 Key/Secret/Token
3. **配置 .env**：将凭证添加到 `.env` 文件
4. **编写拉取函数**：在 `real_data_pull_engine.py` 中添加 `pull_xxx_data()` 函数
5. **测试连通性**：运行 `python scripts/real_data_pull_engine.py --xxx` 验证
6. **接入 Learning Loop**：在 `real_data_bridge.py` 中添加该数据源的格式转换
7. **验证数据真实性**：确认返回数据为真实 API 数据，非模拟/空数据

---

## 数据真实性验证标准

每个 Partner API 接入后，必须满足：

- [ ] API 返回 200 状态码
- [ ] 返回数据包含真实的 conversions/clicks/revenue 字段
- [ ] 数据有明确的时间戳（非静态/缓存数据）
- [ ] 无数据时返回 `REVENUE_NOT_AVAILABLE`，而非 $0 或模拟数值
- [ ] `data_validation_report` 中该数据源标记为 `PASS`
- [ ] Learning Loop 能消费该数据并产出策略变更

---

*文档生成时间：2026-08-31*
*维护者：ChinaBound Travel AI Growth OS*
