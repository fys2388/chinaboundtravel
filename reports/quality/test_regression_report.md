# 测试回归报告

生成时间: 2026-09-21T22:22:42

- 本次运行: 1336 collected, 39 failed
- 基线存量失败: 43
- **新增失败: 0**（阻断条件）
- 已修复的基线失败: 4（建议 --update-baseline 收敛）

## 已修复的基线失败（更新基线可收敛）

- `tests.test_audit_summary_md::test_fail_flag_zero_when_all_pass`
- `tests.test_local_kpi_measures::test_ci_block_rate_on_real_repo_is_fully_wired`
- `tests.test_seo_structured_data_audit::test_cli_json_is_valid_and_complete`
- `tests.test_seo_structured_data_audit::test_cli_plain_output_names_coverage`
