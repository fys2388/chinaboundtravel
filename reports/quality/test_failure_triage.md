# 存量测试失败分类

总数: 39  |  可自动修: 17  |  需人拍板: 5

## stale-test — 过时测试断言（把已知缺陷写死成期望）（17）

**修复动作**: 改测试：用受控夹具替代「断言真实仓库当前状态」。可自动修。

- `tests.test_brand_legacy_pilot::test_title_and_h2_structure_retained`
  - tests\_unknown.py — 测试名含 `title_and_h2_structure_retained`
- `tests.test_growth05_first_content_action::test_144h_title_and_description_updated`
  - tests\_unknown.py — 测试名含 `title_and_description_updated`
- `tests.test_growth07_content_differentiation::test_wechat_meta_descriptions_differ`
  - tests\_unknown.py — 测试名含 `descriptions_differ`
- `tests.test_growth07_content_differentiation::test_wechat_titles_differ`
  - tests\_unknown.py — 测试名含 `titles_differ`
- `tests.test_growth12_revenue_experiment::test_affiliate_destination_unchanged`
  - tests\_unknown.py — 测试名含 `destination_unchanged`
- `tests.test_growth12_revenue_experiment::test_title_unchanged`
  - tests\_unknown.py — 测试名含 `title_unchanged`
- `tests.test_growth16_commercial_expansion::test_rev002_cta_not_modified`
  - tests\_unknown.py — 测试名含 `cta_not_modified`
- `tests.test_growth17_transportation_release::test_rev002_cta_untouched`
  - tests\_unknown.py — 测试名含 `cta_untouched`
- `tests.test_growth18_transportation_card::test_recommended_tools_table`
  - tests\_unknown.py — 测试名含 `recommended_tools_table`
- `tests.test_growth18_transportation_card::test_required_h2_structure`
  - tests\_unknown.py — 测试名含 `required_h2_structure`
- `tests.test_growth18_transportation_card::test_rev002_cta_unchanged`
  - tests\_unknown.py — 测试名含 `cta_unchanged`
- `tests.test_growth19_transportation_cluster::test_airport_recommended_services_table`
  - tests\_unknown.py — 测试名含 `recommended_services_table`
- `tests.test_growth19_transportation_cluster::test_airport_required_h2_structure`
  - tests\_unknown.py — 测试名含 `required_h2_structure`
- `tests.test_growth19_transportation_cluster::test_rev002_cta_unchanged`
  - tests\_unknown.py — 测试名含 `cta_unchanged`
- `tests.test_growth20_monetization::test_rev002_cta_unchanged`
  - tests\_unknown.py — 测试名含 `cta_unchanged`
- `tests.test_growth21_payment_cluster::test_rev002_unchanged`
  - tests\_unknown.py — 测试名含 `rev002_unchanged`
- `tests.test_growth22_payment_release::test_rev002_unchanged`
  - tests\_unknown.py — 测试名含 `rev002_unchanged`

## content-drift — 内容漂移（需改 content/posts/，保护区，需人拍板）（5）

**修复动作**: 先由人决定「恢复内容」还是「更新测试」，然后改。不可自动修。

- `tests.test_growth12a_candidate_lock::test_candidate_has_affiliate_partners`
  - tests\_unknown.py — 测试名含 `candidate_has_affiliate_partners`，修复需改 content/posts/
- `tests.test_growth15_commercial_conversion::test_rev002_cta_exists_once`
  - tests\_unknown.py — 测试名含 `rev002_cta`，修复需改 content/posts/
- `tests.test_growth15_commercial_conversion::test_rev002_partner_trip`
  - tests\_unknown.py — 测试名含 `rev002_partner`，修复需改 content/posts/
- `tests.test_growth15_commercial_conversion::test_rev002_placement_after_booking_section`
  - tests\_unknown.py — 测试名含 `rev002_placement`，修复需改 content/posts/
- `tests.test_growth20_monetization::test_rev002_partner_unchanged`
  - tests\_unknown.py — 测试名含 `rev002_partner`，修复需改 content/posts/

## env-data — 环境/数据依赖（本机凭证或外部数据）（2）

**修复动作**: 配置对应 secret / 凭证；无法配置则改成显式跳过。半自动。

- `tests.test_social_content_agent::test_inventory_has_100_items_and_20_sources`
  - tests\_unknown.py — 命中环境/数据特征 `inventory_has_100_items`
- `tests.test_social_content_agent::test_inventory_platform_balance`
  - tests\_unknown.py — 命中环境/数据特征 `inventory_platform_balance`

## code-defect — 代码缺陷（需逐个人工看）（15）

**修复动作**: 逐个人工排查。不可自动修。

- `tests.test_agent_kpi_data_integrity::test_daily_report_values_are_real_measurements`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_avatar_webp::test_about_hero_prefers_webp`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_avatar_webp::test_profile_mode_uses_webp`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_avatar_webp::test_schema_json_still_has_avatar`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_avatar_webp::test_sidebar_prefers_webp`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_brand_consistency_audit::test_brand_commit_step_is_non_fatal`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_growth05_first_content_action::test_growth05_scope_only_allowed_objects`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_okr_and_experiment_semantics.TestDaysSinceLastPost::test_counts_quoted_dates`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_okr_and_experiment_semantics.TestOkrFakeGreen::test_note_is_rendered_into_the_table`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_okr_and_experiment_semantics.TestOkrFakeGreen::test_zero_new_content_is_not_green`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_okr_and_experiment_semantics.TestZeroRunEscalation::test_content_new_escalates_when_overdue`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_secret_name_contract::test_no_forbidden_synonym_secret_names`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_security_headers_audit::test_record_check_failure_is_wired_into_all_network_checks`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_site_health_dashboard_regen::test_regen_step_surfaces_failures`
  - tests\_unknown.py — 无自动特征命中，需人工看
- `tests.test_social_analytics_metrics::test_posts_query_uses_current_buffer_input_contract`
  - tests\_unknown.py — 无自动特征命中，需人工看
