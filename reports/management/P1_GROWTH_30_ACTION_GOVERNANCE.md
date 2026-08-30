# P1-GROWTH-30 — Action Governance

- Date: 2026-08-29
- 目标：把“谁能执行、什么必须审批、什么必须等”变成确定性规则。

## 治理等级

| 等级 | 判定条件 | 示例 |
|---|---|---|
| AUTO_ACTION | 机械性、可逆、无事实语义变化 | 安全格式修复、已知 legacy 人称替换、社媒排期 |
| REVIEW_REQUIRED | 涉及内容改写、不确定事实、商业 CTA、归因变化 | FACT_CHECK 后重写、新增 CTA、affiliate attribution 变更 |
| WAIT | 样本不足、等待 recrawl、缺收入数据 | 新页观察 28d、GROWTH07B/07C recrawl、revenue API 未接入 |
| FROZEN | 活动实验、评审门未到 | REV001/REV002/REV003、GROWTH05、GROWTH28 pilot、DRIVE-001 |

## 动作 -> 治理映射

| 推荐动作 | 治理等级 | 说明 |
|---|---|---|
| FROZEN | FROZEN | 只观察，不执行 |
| WAIT | WAIT | 不执行，等待外部状态 |
| MONITOR | WAIT | 观察数据积累，不做内容变更 |
| FACT_CHECK | REVIEW_REQUIRED | 核对官方来源并注明日期 |
| TECHNICAL_FIX | REVIEW_REQUIRED | canonical/索引/重定向需技术评审 |
| OPTIMIZE | REVIEW_REQUIRED | 标题/meta/H1/内链改动需审批 |
| SCALE | REVIEW_REQUIRED | 扩量涉及 CTA 或归因变化，需审批 |

## 确定性门槛

1. 只要 `status = FROZEN`，任何 AUTO_ACTION 都不得触碰该页面。
2. 只要存在 FACT_CHECK_REQUIRED，重写动作必须先完成事实核查。
3. 只要等待 recrawl 或 canonical 冲突未关闭，不得做 SEO 内容优化。
4. revenue 数据缺失时，禁止宣称转化/收入效果，只做 MONITOR/WAIT。
5. AUTO_ACTION 必须可回滚并记录 before/after。
