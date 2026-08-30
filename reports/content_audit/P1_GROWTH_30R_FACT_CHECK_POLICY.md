# P1-GROWTH-30R — Fact Check Governance

- Date: 2026-08-29
- Source: `CONTENT_TRUST_AUDIT.csv` + `P1_GROWTH_30_TRUST_DECISION_MODEL.csv`
- Queue: `reports/content_audit/P1_GROWTH_30R_FACT_CHECK_QUEUE.csv`
- 本轮不修改文章，只建立证据策略与队列。

## 证据类别

| 类别 | 队列数量 |
|---|---:|
| prices / fees | 160 |
| visa / immigration | 119 |
| opening hours | 50 |
| law / regulation | 43 |
| distances / durations | 37 |
| transportation | 26 |
| schedules | 0 |
| current availability | 0 |
| unclassified | 44 |
| 合计 | 479 |

## 确定性规则

1. **已有已验证来源**：`source_status = VERIFIED`，允许受控修正（来源 + 日期
   必须记录，禁止自行推导）。
2. **无已验证来源**：`source_status = NO_VERIFIED_SOURCE`，不得编造事实。
3. **保守改写**：可在人工确认后移除无支持的精确主张（价格、时刻、时限、距离、
   政策细节），不得引入新事实。
4. **记录三要素**：每行必须记录 `source_status`、`evidence_required`、
   `action`。

## 字段说明

- `source_status`：`VERIFIED` / `NO_VERIFIED_SOURCE`
- `evidence_required`：核验所需官方来源类型与日期要求
- `action`：当前统一为 `VERIFY_OR_REMOVE`

## 执行门

- 所有 FACT_CHECK_REQUIRED 均为 `REVIEW_REQUIRED`。
- 未核验前禁止 OPTIMIZE / SCALE / 重写。
- 本轮只产出队列，不批量修改 479 个问题。
