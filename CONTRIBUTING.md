# Contributing Guide

本项目的贡献者铁律。**AGENTS.md** 已经写了通用行为纪律（agent 侧），本文件写**人类/代码贡献侧**的具体闸门，尤其是历史上踩过的坑。

---

## 1. MailerLite 订阅者卫生（AUDIT-OPS-005 / OPS-006 沉淀）

**铁律**：`POST https://connect.mailerlite.com/api/subscribers` 或 `/api/subscribe` 时，`body.email` **必须**是 `scripts/ml_utils.py::TEST_EMAIL_WHITELIST` 里的固定字符串。**禁止**用 `test-<timestamp>@example.com`、`user-<uuid>@example.com` 这类动态生成邮箱。

### 为什么

MailerLite 幂等去重按 email：同名 email 二次 POST 会**更新**已有记录，而不是新增。动态邮箱每次都是新的 email，直接污染订阅者库，且删起来要一条条调 API DELETE。历史事故：09-18 / 09-20 的 3 个 curl 手动探针 + 已删除的旧脚本共向 MailerLite 塞了 7 个 `@example.com` 假订阅者，触发 AUDIT-OPS-005/006 排查。

### 允许的固定测试邮箱（3 个，与 `ml_utils.py::TEST_EMAIL_WHITELIST` 严格同步）

| 用途 | 邮箱 |
|---|---|
| 订阅健康审计 | `healthcheck.chinaboundtravel@example.com` |
| API 连通性检查 | `test-api-health@example.com` |
| 性能监控探针 | `perf-test@example.com` |

如必须新增第 4 个：**先**改 `scripts/ml_utils.py::TEST_EMAIL_WHITELIST` 和 `scripts/lint/check_mailerlite_hygiene.py::ALLOWED_TEST_EMAILS`（两处必须同步），**再**改脚本。任何一处漏改 lint 会 exit 1。

### Lint gate（合并前必须绿）

```bash
python scripts/lint/check_mailerlite_hygiene.py
```

扫 6 个 MailerLite 相关脚本（`subscription_health_audit.py` / `api_health_audit.py` / `performance_monitor.py` / `mailerlite_sequence_setup.py` / `email_sequence_tracker.py` / `ml_utils.py`）里的所有 `@example.com/.org/.net` 字符串字面量，跳过 docstring，命中但不在白名单 → exit 1。

- 建议接入 `site-health-daily.yml` 或 pre-merge gate。
- 集成建议：新增脚本时若涉及 MailerLite 调用，把文件名加入 `scripts/lint/check_mailerlite_hygiene.py::MAILERLITE_RELATED_SCRIPTS`。

### Token 卫生（AUDIT-OPS-005 沉淀）

MailerLite API token 在 `.env` 里可能带 UTF-8 BOM（`\ufeff`），`requests` 拼 `Authorization` header 时 latin-1 encode 会炸。**任何读取 `.env` MailerLite token 的地方**都**必须**走 `scripts/ml_utils.py::get_mailerlite_token()`（内部会 `clean_token` 剥 BOM），不要自己 `os.environ.get(...)` 直接用。

已接线的 9 个脚本：`scripts/ml_utils.py` / `scripts/subscription_health_audit.py` / `scripts/api_health_audit.py` / `scripts/performance_monitor.py` / `scripts/mailerlite_sequence_setup.py` / `scripts/email_sequence_tracker.py` / `scripts/audit_okr_achievement.py` / `scripts/feishu_daily_report.py` / `scripts/feishu_weekly_report.py` / `scripts/feishu_monthly_report.py` / `scripts/feishu_quarterly_report.py` / `scripts/feishu_yearly_report.py`。新增脚本若走 MailerLite，同样接入。

### 假订阅者清理链（如果又回来了）

MailerLite 当前状态：1 个真实订阅者（`fys2388@gmail.com`）+ 3 个白名单固定测试邮箱。**0 个 `@example.com` 污染源**。

若某天又看到 `@example.com` 假订阅者，一条命令清理（dry-run 默认）：

```bash
python scripts/subscription_health_audit.py --cleanup           # 只报告不删
python scripts/subscription_health_audit.py --cleanup --cleanup-apply  # 真删
```

清理链设计：
- 只删 RFC 6761/6762 保留域名（`@example.com/.org/.net`），永不触碰真实邮箱
- 跳过 `TEST_EMAIL_WHITELIST` 里的 3 个固定测试邮箱（它们是幂等的，保留作为"系统运行过"证据）
- 默认 `dry_run=True` 只报告不删，`--cleanup-apply` 才真删，防误删

---

## 2. Git 工作流

- **push 由人做**，不由 agent 做。agent 只 `commit`，不 `push`。
- 破坏性 git 命令（`stash` / `reset --hard` / `checkout --` / `clean` / `push -f` / `branch -D`）**禁止**，见 `AGENTS.md`。
- Push 前 `git pull --rebase --autostash` 拉取远端变更并 rebase，避免 push 被拒。
- 用 `git mv` 保留 rename 历史，不要 `rm` + `add`。

## 3. 敏感文件（绝对禁止 commit）

- `.env`
- `config/service-account.json`
- `gsc-service-account-key.json`

不 `cat` / `read` / `commit`，不输出到对话。

## 4. `_draft/` 目录约定

- `content/posts/`：只放**已发布**文章。
- `content/_draft/`：所有 `draft: true` 的草稿统一放这里（不参与构建发布）。
- 同一 slug 只保留**最新一次** attempt（如 `-attempt3.md`），历史 attempt 用 `git rm` 精简（git 历史仍可找回）。

## 5. 报告与 ledger

- 审计报告落 `reports/daily_report_audit/ISSUE_TRACKING_LEDGER_*.json`，每轮修复**必须**在 `fix_runs[]` 追加一条记录（`run_id` / `fixes_applied` / `changed_files` / `verification` / `residual` / `commit_sha`）。
- `summary.total_open` / `total_resolved` / `by_status` 等计数器与 `issues[]` 实际状态必须一致。
- `reports/llm/` 是本地 LLM 缓存，untracked，**不要** git add。

---

_最后更新：2026-09-23（AUDIT-OPS-005/006 沉淀）。修改本文件前请确认 lint gate 与白名单双向同步。_
