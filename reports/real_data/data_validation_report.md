# 数据真实性和新鲜度验证报告

**验证时间**: 2026-09-24 10:41:20
**整体状态**: PASS

---

## 验证概览

| 数据源 | 真实数据 | 新鲜度 | 数据日期 | API状态 | 验证状态 |
|--------|---------|--------|---------|---------|---------|
| GA4 | ✅ | ✅ | 2026-09-23 | OK | PASS |
| GSC | ✅ | ✅ | 2026-09-21 | OK | PASS |
| SOCIAL | ✅ | ✅ | 2026-09-24 | OK | PASS |
| CONTENT | ✅ | ✅ | 2026-09-24 | UNKNOWN | PASS |
| PARTNERIZE | ⏸ | ⏸ | N/A | DISABLED_BY_DECISION | DISABLED |
| IMPACT | ⏸ | ⏸ | N/A | DISABLED_BY_DECISION | DISABLED |
| MULTI_PARTNER | ⏸ | ⏸ | N/A | DISABLED_BY_DECISION | DISABLED |

---

## 统计

- 真实数据源: 4/4
- 新鲜数据源: 4/4
- 已决策停用: 3（impact, multi_partner, partnerize）
- 问题数: 0

---

## 问题清单

无问题，所有活动数据源均为真实且新鲜的数据。

---

## 已决策停用的数据源（非故障，不计入通过率）

- **impact**: 同上——Impact 网络上本站点无在册品牌，NordVPN 走 affiliatescn 不经 Impact。
- **multi_partner**: 依赖 partnerize/impact 连接状态聚合，上游已停用。
- **partnerize**: World Nomads 走 Impact 被拒、Allianz 无公开联盟计划；两计划已移出 hugo.toml，本源无承载对象。

恢复步骤：确认联盟计划已获批 → 把 key 加回 `hugo.toml [params.affiliate]` → 从 `DISABLED_SOURCES` 删除。

---

## 修复指引

- **GA4 NOT_CONFIGURED**: 在 .env 或 GitHub Secrets 中设置 GA4_PROPERTY_ID，并确保 service account 已添加为 GA4 媒体资源的查看者
- **GSC SITE_ACCESS_DENIED**: 在 Google Search Console > Settings > Users and permissions 中添加 service account 邮箱（角色：Full 或 Restricted）
- **Social NOT_CONFIGURED**: 在 .env 或 GitHub Secrets 中设置共享的 BUFFER_API_TOKEN_A 和 BUFFER_API_TOKEN_B

---

*报告由真实数据拉取引擎 v2.1 自动生成*
*生成时间: 2026-09-24 10:41:20*
