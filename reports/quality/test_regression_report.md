# 测试回归报告

生成时间: 2026-09-22T11:56:16

- 本次运行: 6 collected, 6 failed
- 基线存量失败: 16
- **新增失败: 6**（阻断条件）
- 已修复的基线失败: 16（建议 --update-baseline 收敛）

## 新增失败（需要处理）

- `tests.test_generation_failure_logging`

- `tests.test_predeploy_quality_gate`

- `tests.test_seo_optimizer_logic`

- `tests.test_site_health_dashboard_regen`

- `tests.test_workflow_names`

- `tests.test_workflow_yaml`

## 已修复的基线失败（更新基线可收敛）

- `tests.test_agent_kpi_data_integrity::test_daily_report_values_are_real_measurements`
- `tests.test_avatar_webp::test_about_hero_prefers_webp`
- `tests.test_avatar_webp::test_profile_mode_uses_webp`
- `tests.test_avatar_webp::test_schema_json_still_has_avatar`
- `tests.test_avatar_webp::test_sidebar_prefers_webp`
- `tests.test_brand_consistency_audit::test_brand_commit_step_is_non_fatal`
- `tests.test_okr_and_experiment_semantics.TestDaysSinceLastPost::test_counts_quoted_dates`
- `tests.test_okr_and_experiment_semantics.TestOkrFakeGreen::test_note_is_rendered_into_the_table`
- `tests.test_okr_and_experiment_semantics.TestOkrFakeGreen::test_zero_new_content_is_not_green`
- `tests.test_okr_and_experiment_semantics.TestZeroRunEscalation::test_content_new_escalates_when_overdue`
- `tests.test_secret_name_contract::test_no_forbidden_synonym_secret_names`
- `tests.test_security_headers_audit::test_record_check_failure_is_wired_into_all_network_checks`
- `tests.test_site_health_dashboard_regen::test_regen_step_surfaces_failures`
- `tests.test_social_analytics_metrics::test_posts_query_uses_current_buffer_input_contract`
- `tests.test_social_content_agent::test_inventory_has_100_items_and_20_sources`
- `tests.test_social_content_agent::test_inventory_platform_balance`
