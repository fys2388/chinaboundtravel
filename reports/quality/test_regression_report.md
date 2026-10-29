# 测试回归报告

生成时间: 2026-10-29T13:30:47

- 本次运行: 1350 collected, 23 failed
- 基线存量失败: 16
- **新增失败: 9**（阻断条件）
- 已修复的基线失败: 2（建议 --update-baseline 收敛）

## 新增失败（需要处理）

- `tests.test_brand_legacy_pilot::test_title_and_h2_structure_retained`

- `tests.test_okr_and_experiment_semantics.TestCiWindow::test_success_and_failure_are_unaffected_by_window`

- `tests.test_okr_and_experiment_semantics.TestExperimentPhantom::test_registry_age_days_detects_stale`

- `tests.test_okr_and_experiment_semantics.TestExperimentPhantom::test_running_in_snapshot_but_planned_in_config_is_not_started`

- `tests.test_okr_and_experiment_semantics.TestZeroRunEscalation::test_content_new_within_cadence_stays_green`

- `tests.test_okr_and_experiment_semantics.TestZeroRunEscalation::test_unresolvable_date_keeps_original_icon`

- `tests.test_redirect_chains::test_finals_are_not_redirect_sources`

- `tests.test_redirect_chains::test_no_redirect_chains`

- `tests.test_social_content_agent::test_image_prompt_present`

## 已修复的基线失败（更新基线可收敛）

- `tests.test_agent_kpi_data_integrity::test_daily_report_values_are_real_measurements`
- `tests.test_okr_and_experiment_semantics.TestOkrFakeGreen::test_zero_new_content_is_not_green`
