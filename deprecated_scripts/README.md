# ⚠️ DEPRECATED SCRIPTS (已废弃)

> 最后清理: 2026-09-20

## 状态

本目录包含 **55 个已废弃脚本**，保留仅供历史参考，**不应被任何工作流调用**。

## 废弃原因分类

| 分类 | 数量 | 说明 |
|------|------|------|
| 编码修复 | ~12 | `fix_encoding_*.py`、`clean_garbled.py`、`find_chinese_chars.py` 等，一次性修复已完成 |
| 测试/调试 | ~8 | `test_*.py`，功能已合并到 `tests/` 目录 |
| 旧版发布 | ~5 | `auto_bomber.py`、`agent_pipeline.py`、`content_pipeline.py`，已由 `run_all_agents.py` 替代 |
| 部署/配置 | ~5 | `deploy_ebook.py`、`configure_github_secrets.py`、`verify_cloudflare_secrets.py`，已迁移到 workflow |
| 数据校验 | ~6 | `check_*.py`、`verify_*.py`，已由 `site_health_agent.py` 替代 |
| 内容处理 | ~4 | `batch_fix_images.py`、`fix_frontmatter*.py`，已由 `content_intelligence_agent.py` 替代 |
| 其他 | ~15 | `gen_pdf.py`、`write_gen.py`、`update_prices.py` 等，功能已下线或迁移 |

## 替代方案

| 旧脚本 | 替代脚本 |
|--------|---------|
| `agent_pipeline.py` / `content_pipeline.py` | `scripts/run_all_agents.py` |
| `check_encoding*.py` / `fix_encoding*.py` | `scripts/site_health_agent.py` |
| `clean_garbled.py` / `find_chinese_chars.py` | `scripts/site_health_agent.py` |
| `auto_bomber.py` | `scripts/social_intelligence_agent.py` |
| `daily_inspection.py` / `boundtravel_daily_inspector.py` | `scripts/agent_kpi_auditor.py` |
| `test_buffer_api.py` | `scripts/test_buffer_api.py` (scripts 目录) |
| `configure_github_secrets.py` | GitHub Actions Secrets UI |

## 清理建议

如果确认不再需要历史参考，可以安全删除本目录。当前保留是为了：
1. 审计追溯（确认旧功能已下线）
2. 调试参考（某些旧逻辑可能有参考价值）
3. 避免意外删除导致的不可逆操作

## 注意事项

- ❌ 不要在 workflow 中引用本目录的脚本
- ❌ 不要将本目录的脚本加入 `scripts/` 目录
- ✅ 如果需要恢复某个功能，请在 `scripts/` 中重新实现
