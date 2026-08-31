# 数据真实性和新鲜度验证报告

**验证时间**: 2026-08-31 07:36:39
**整体状态**: FAIL

---

## 验证概览

| 数据源 | 真实数据 | 新鲜度 | 数据日期 | API状态 | 验证状态 |
|--------|---------|--------|---------|---------|---------|
| GA4 | ❌ | ❌ | None | NOT_CONFIGURED | FAIL |
| GSC | ❌ | ❌ | None | NOT_CONFIGURED | FAIL |
| SOCIAL | ❌ | ❌ | None | NOT_CONFIGURED | FAIL |
| CONTENT | ✅ | ✅ | 2026-08-31 | UNKNOWN | PASS |
| PARTNERIZE | ❌ | ❌ | None | NO_CREDENTIALS | FAIL |
| IMPACT | ❌ | ❌ | None | NO_CREDENTIALS | FAIL |
| MULTI_PARTNER | ❌ | ❌ | None | NO_CONNECTED_PARTNERS | FAIL |

---

## 统计

- 真实数据源: 1/4
- 新鲜数据源: 1/4
- 问题数: 6

---

## 问题清单

1. ga4: NOT_CONFIGURED - GA4_PROPERTY_ID not set in .env or GitHub Secrets
2. gsc: NOT_CONFIGURED - GSC_SERVICE_ACCOUNT_JSON not configured
3. social: NOT_CONFIGURED - BUFFER_API_TOKEN_A/B not configured
4. partnerize: NO_CREDENTIALS - not real data
5. impact: NO_CREDENTIALS - not real data
6. multi_partner: NO_CONNECTED_PARTNERS - not real data

---

## 修复指引

- **GA4 NOT_CONFIGURED**: 在 .env 或 GitHub Secrets 中设置 GA4_PROPERTY_ID，并确保 service account 已添加为 GA4 媒体资源的查看者
- **GSC SITE_ACCESS_DENIED**: 在 Google Search Console > Settings > Users and permissions 中添加 service account 邮箱（角色：Full 或 Restricted）
- **Social NOT_CONFIGURED**: 在 .env 或 GitHub Secrets 中设置 BUFFER_API_TOKEN_A 和 BUFFER_API_TOKEN_B

---

*报告由真实数据拉取引擎 v2.1 自动生成*
*生成时间: 2026-08-31 07:36:39*
