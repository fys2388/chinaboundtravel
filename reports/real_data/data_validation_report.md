# 数据真实性和新鲜度验证报告

**验证时间**: 2026-09-05 09:35:52
**整体状态**: PASS

---

## 验证概览

| 数据源 | 真实数据 | 新鲜度 | 数据日期 | API状态 | 验证状态 |
|--------|---------|--------|---------|---------|---------|
| GA4 | ✅ | ✅ | 2026-09-04 | OK | PASS |
| GSC | ✅ | ✅ | 2026-09-02 | OK | PASS |
| SOCIAL | ✅ | ✅ | 2026-09-05 | OK | PASS |
| CONTENT | ✅ | ✅ | 2026-09-05 | UNKNOWN | PASS |
| PARTNERIZE | ❌ | ❌ | None | NO_CREDENTIALS | FAIL |
| IMPACT | ❌ | ❌ | None | NO_CREDENTIALS | FAIL |
| MULTI_PARTNER | ❌ | ❌ | None | NO_CONNECTED_PARTNERS | FAIL |

---

## 统计

- 真实数据源: 4/4
- 新鲜数据源: 4/4
- 问题数: 3

---

## 问题清单

1. partnerize: NO_CREDENTIALS - not real data
2. impact: NO_CREDENTIALS - not real data
3. multi_partner: NO_CONNECTED_PARTNERS - not real data

---

## 修复指引

- **GA4 NOT_CONFIGURED**: 在 .env 或 GitHub Secrets 中设置 GA4_PROPERTY_ID，并确保 service account 已添加为 GA4 媒体资源的查看者
- **GSC SITE_ACCESS_DENIED**: 在 Google Search Console > Settings > Users and permissions 中添加 service account 邮箱（角色：Full 或 Restricted）
- **Social NOT_CONFIGURED**: 在 .env 或 GitHub Secrets 中设置 BUFFER_API_TOKEN_A 和 BUFFER_API_TOKEN_B

---

*报告由真实数据拉取引擎 v2.1 自动生成*
*生成时间: 2026-09-05 09:35:52*
