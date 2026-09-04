# ChinaBound Travel 2.1 Agent 责任架构 v2.0

## 核心原则
- **横向巡检 + 垂直优化**：Site Health Agent负责横向发现，垂直Agent负责深度优化
- **发现即分配**：任何Agent发现问题立即进入daily_issue_router分配
- **低风险自动修复**：L2权限Agent可自动执行明确的低风险修复
- **修复必验证**：所有自动修复后必须运行验证检查
- **经验必沉淀**：修复结果进入Growth Memory，更新巡检规则

## Agent责任矩阵

### 1. Site Health Agent (L2) — 新增
**定位**：网站健康巡检 + 低风险自动修复
**巡检范围**：
- Sitemap健康：301页、noindex页、404页、重复URL
- Meta/Robots：noindex/nofollow/canonical配置正确性
- 配置一致性：工作流env与Secrets匹配、变量名引用正确
- 文件健康：JSON/MD编码、乱码检测、占位符残留
- 内容完整性：空链接、图片缺alt、Review needed标记
- 死链检测：内链404
- 性能基础：页面可访问性、响应码

**自动修复权限（L2）**：
- ✅ 添加/移除noindex、robotsdisallow
- ✅ sitemap排除（_build: list:false）
- ✅ 格式规范化、编码修复
- ✅ 占位符标记清理（前台暴露的状态标记）
- ✅ 图片alt补全（从文件名推断）
- ⚠️ 内容修改 → 生成PR待审核
- ❌ URL结构变更、大规模删除

### 2. SEO Agent (L2) — 扩展
**原职责**：Title优化、关键词分析
**新增职责**：
- 技术SEO深度检查（结构化数据、hreflang、canonical冲突）
- GSC数据异常检测（索引错误、点击率骤降）
- 内链结构优化建议

### 3. Content Agent (L1→L2) — 升级
**原职责**：格式规范化、Persona清理
**新增职责**：
- 内容完整性巡检（占位符、空段落、待审核标记）
- AI痕迹检测（模式化比喻、重复信息）
- 内容生命周期管理（DRAFT→PUBLISHED→GROWING→STABLE→DECLINING）
- 低风险内容修复自动执行（格式、Persona、明显错误）

### 4. Social Agent (L2) — 保持
**职责**：Hook优化、发布时间优化、内容适配
**新增闭环要求**：
- 每条社媒必须含UTM链接（引流闭环）
- 社媒数据回传后自动分析CTR/转化率

### 5. Conversion Agent (L2) — 保持
**职责**：CTA优化、A/B测试、漏斗分析
**新增**：
- 联盟链接健康检查（404、重定向、参数丢失）

### 6. Revenue Agent (L1) — 保持
**职责**：收入分析、Partner审计
**新增**：
- 联盟API连通性每日检查
- 收入数据异常告警

### 7. User Agent (L1) — 保持
**职责**：用户分析、分群、旅程分析

### 8. Self-Learning Agent (L0) — 保持
**职责**：模式提取、策略建议（只读）

## 闭环工作流

```
Site Health每日巡检
    ↓
发现问题（带严重程度分类）
    ↓
daily_issue_router.py 自动分配
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│  L2 自动修复     │  L1 生成修复建议  │  L3 人工审核     │
│  (noindex/sitemap│  (内容/结构建议)  │  (事实/政策/财务) │
│   /格式/编码)    │                 │                 │
└─────────────────┴─────────────────┴─────────────────┘
    ↓
自动验证（measure_validation_engine）
    ↓
修复成功 → Growth Memory沉淀 → 更新巡检规则
修复失败 → 回滚 → 升级为人工任务
```

## 问题严重程度与响应

| 级别 | 定义 | 响应时间 | 执行方式 |
|---|---|---|---|
| P0 Critical | 网站不可用、数据断裂、安全问题 | 立即 | Site Health自动修复+告警 |
| P1 High | 影响SEO/转化的技术问题 | 24h内 | L2 Agent自动修复 |
| P2 Medium | 内容质量、用户体验 | 本周 | L1生成建议+人工确认 |
| P3 Low | 优化建议、锦上添花 | 排期 | 进入backlog |

## 与现有系统集成
- 巡检结果 → `reports/site_health/` 目录
- 问题分配 → `reports/daily_issues/agent_tasks/`
- 修复记录 → `reports/growth_memory/`
- 每日汇总 → 飞书日报新增"Site Health"板块
