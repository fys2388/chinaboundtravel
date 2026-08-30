# P1-GROWTH-30 — Content Trust Decision Model

- Date: 2026-08-29
- Source: `reports/content_audit/CONTENT_TRUST_AUDIT.csv`（862 条 issue）
- Output: `reports/content_audit/P1_GROWTH_30_TRUST_DECISION_MODEL.csv`

## 分类结果

| 决策 | 数量 | 含义 |
|---:|---:|---|
| AUTO_FIX | 294 | 已知 legacy 人称、中文残留、确定性 SEO 格式 |
| SAFE_NORMALIZE | 89 | 明显夸大但语义可保留的措辞、需人工选择的内链补充 |
| FACT_CHECK_REQUIRED | 479 | 动态事实与无来源数字，必须核对官方来源 |
| NO_CHANGE | 0 | 本轮未命中（规则保留，供未来误报使用） |
| 合计 | 862 | |

## 确定性规则

| 输入条件 | 决策 | 理由 |
|---|---|---|
| `issue_type = 品牌风险` | AUTO_FIX | 已知 legacy 人称/本地宣称，机械改编辑部口吻 |
| `issue_type = 中文残留` | AUTO_FIX | 明显不需要的中文，翻译或移除 |
| `AI幻觉` + 虚构个人经历 | AUTO_FIX | 已知 legacy 人称规则 |
| `SEO问题` + 标题/描述/H2 | AUTO_FIX | 确定性 SEO 格式问题 |
| `AI幻觉` + 绝对化/无依据描述 | SAFE_NORMALIZE | 弱化语气且语义保留 |
| `SEO问题` + 内部链接 | SAFE_NORMALIZE | 需人工选链，低风险规范化 |
| `issue_type = 事实风险` | FACT_CHECK_REQUIRED | visa/policy/law/price/fee/hours/schedule/distance/availability |
| `AI幻觉` + 无来源数据 | FACT_CHECK_REQUIRED | 数值、价格、里程等主张 |
| 未命中规则 | NO_CHANGE | 保留人工复核 |

## 硬性约束

- **NEVER invent replacement facts**：FACT_CHECK_REQUIRED 项只能核对官方来源后
  更新，禁止用模型知识补写事实。
- 每一条动态事实修正必须注明核对日期和来源。
- AUTO_FIX 只执行机械性、确定性替换；涉及语义判断的改写全部降级为
  SAFE_NORMALIZE 或 REVIEW_REQUIRED。
- 本审计 CSV 生成于 2026-08-26；执行修复前应重新运行
  `python scripts/content_trust_audit.py`，避免修改已修复内容。

## 后续流转

1. AUTO_FIX -> `AUTO_ACTION`（小批量、带 before/after 记录）
2. SAFE_NORMALIZE -> `REVIEW_REQUIRED`（人工或规则预览）
3. FACT_CHECK_REQUIRED -> `REVIEW_REQUIRED`（官方来源 + 日期）
4. NO_CHANGE -> 不进入执行队列
