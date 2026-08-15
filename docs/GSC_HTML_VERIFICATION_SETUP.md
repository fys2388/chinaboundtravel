# GSC HTML Verification Setup

- **日期**：2026-08-15
- **状态**：HTML tag 验证 **未激活**（`hugo.toml` 中 `SiteVerificationTag` 为空、`googleSearchConsole` 为占位符）
- **API 链路**：✅ 已通过 service account 打通（`scripts/verify_gsc_access.py` = OK）
- **说明**：GSC API 数据读取与 HTML 验证是两条独立链路。API 已可用，HTML tag 仅影响"站点所有权验证方式"，建议改用 DNS TXT 验证（无需改代码）。

## 推荐：DNS TXT 验证（无需代码变更）

| 项 | 值 |
|---|---|
| Property | `https://www.chinaboundtravel.com/`（URL-prefix） |
| DNS Host | `chinaboundtravel.com`（apex TXT） |
| DNS TXT name | `@`（或按 Cloudflare DNS 面板提示） |
| DNS TXT value | 由 Google Search Console 生成（每个账号不同，从 GSC 后台复制） |
| TTL | 3600（默认即可） |

### 操作步骤
1. 登录 [Google Search Console](https://search.google.com/search-console)
2. 选择/添加 property：`https://www.chinaboundtravel.com/`（URL-prefix，含 https、www、尾斜杠）
3. 验证方式选择 **DNS**（Domain provider）
4. Google 给出 TXT 记录（形如 `google-site-verification=...`）
5. 在 Cloudflare DNS → `chinaboundtravel.com` zone 添加 TXT 记录
6. 回 GSC 点击"验证"，等待 DNS 生效（通常几分钟）

### 备选：HTML tag 方式（需改 hugo.toml）
1. GSC → 验证方式 → HTML tag，复制 `content` 值（形如 `abcdef1234567890`）
2. 编辑 `hugo.toml`：
   - `[params.analytics] google = { SiteVerificationTag = "<content 值>", TrackingID = "G-GECBME3YVJ" }`
   - 或设置 `googleSearchConsole = "google-site-verification=<content 值>"`
3. 重新构建并部署后回 GSC 验证
4. ⚠️ 不要将占位符 `YOUR_VERIFICATION_CODE` 提交进仓库

### 当前结论
- API 数据链路：**PASS**（service account 可读 Search Console 数据）
- HTML/DNS 站点验证：**PENDING**（不影响 API 数据读取；建议 DNS TXT 方式完成所有权验证）
- 本文档不包含任何真实验证码值（避免泄露/误提交）
