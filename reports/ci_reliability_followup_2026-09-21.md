# CI 闭环可靠性修复报告（跟进 t5）· 2026-09-21

**修复对象**：`.github/workflows/ops-dashboard-hourly.yml` + `.github/workflows/deploy-cloudflare-pages.yml`
**修复人**：ci-reliability（AgentTeams · chinabound-prod-hardening · t11）
**依赖**：`reports/ci_reliability_fix_2026-09-21.md`（t5 修复报告，标出了本次要修的同类遗留缺陷）
**约束**：未触发任何部署 / push；仅改 YAML + 写本报告；不放松任何现有质量闸门

---

## 0. 修复摘要

| 问题 | 文件 | 行号 | 根因 | 修法 |
|---|---|---|---|---|
| push 前无 rebase | `ops-dashboard-hourly.yml` | L89 | `git push origin main` 直接执行，无 rebase；本仓库多个机器人每 ~30 分钟提交，push 被拒是常态 | 在 push 前加 `git pull --rebase --autostash origin main`，rebase/push 失败时给 `::error::` + exit 1 |
| rebase 缺 `--autostash` | `deploy-cloudflare-pages.yml` | L133（manifest） | `git pull --rebase origin main` 无 `--autostash`，遇 unstaged changes 失败（与 quality-monitor 同根因） | 加 `--autostash`；`exit 0` → `exit 1` + `::error::` |
| rebase 失败后 `exit 0` 静默 | `deploy-cloudflare-pages.yml` | L91（quality data） | `git pull --rebase --autostash origin main \|\| { ...; exit 0; }` — rebase 失败后 exit 0 = step 成功，job 显示绿勾 | 改为 `exit 1` + `::error::` + `continue-on-error: true`（失败可见但不阻断部署） |
| rebase 失败后 `exit 0` 静默 | `deploy-cloudflare-pages.yml` | L157（brand audit） | 同上 | 同上 |

**设计偏差**：无。修法与 t5 一致，与 captain 建议一致。

---

## 1. ops-dashboard-hourly.yml 改动详情

**改动范围**：L88-90（原）→ L88-100（新），+10 行。

**改前**：
```yaml
            git commit -m "chore(ops): auto-refresh dashboard $(date -u '+%Y-%m-%d %H:%M')"
            git push origin main
            echo "Dashboard updated and pushed"
```

**改后**（关键行）：
```yaml
            git commit -m "chore(ops): auto-refresh dashboard $(date -u '+%Y-%m-%d %H:%M')"
            # push 前必须 rebase：多个机器人每 ~30 分钟向 main 提交，push 被拒
            # 是常态（见 AGENTS.md "自动化并发纪律"）。--autostash 处理工作区残留。
            git pull --rebase --autostash origin main || {
              echo "::error title=Rebase 冲突::ops-dashboard commit 无法 rebase，请人工介入"
              git rebase --abort 2>/dev/null || true
              exit 1
            }
            git push origin main || {
              echo "::error title=Push 失败::ops-dashboard commit 已 commit 但 push 被拒（多个机器人每 ~30 分钟提交，push 被拒是常态）"
              exit 1
            }
            echo "Dashboard updated and pushed"
```

**为什么这样改**：
- 本仓库多个机器人每 ~30 分钟向 main 提交，push 被拒是常态（AGENTS.md 明说 2026-09-16 一小时内被拒 2 次）。`ops-dashboard-hourly.yml` cron 是 `*/30 1-18 * * *`（每 30 分钟），正是冲突高发窗口。
- `--autostash` 处理工作区残留（`collect_data.py`、`build.py`、`inject_range_selector.py` 可能写到 git add 白名单之外的目录）。
- `::error::` + `exit 1` 让 rebase/push 失败时给出可读告警，不再静默。
- 如果 push 失败，`gh workflow run "Post-deploy Tasks"` 不会执行。但 push 本身已经触发 deploy（deploy-cloudflare-pages.yml 的 `on: push paths: [static/**]` 匹配 static/ops-dashboard/ 与 static/ops/），所以 `gh workflow run` 是冗余触发器，不执行无影响。

---

## 2. deploy-cloudflare-pages.yml 改动详情

**改动范围**：3 个 step 修改。

### 2.1 "Publish quality data for ops dashboard" step（原 L79-92 → 新 L79-103）

**改前**：
```yaml
      - name: Publish quality data for ops dashboard
        if: always()
        run: |
          ...
          git pull --rebase --autostash origin main || { git rebase --abort 2>/dev/null || true; echo "rebase failed"; exit 0; }
          git push origin main || echo "quality report push failed (non-fatal)"
```

**改后**（关键行）：
```yaml
      - name: Publish quality data for ops dashboard
        if: always()
        continue-on-error: true
        run: |
          ...
          git commit -m "chore(quality): publish post-deploy quality gate [skip ci]"
          # --autostash 已存在；把 exit 0 改为 exit 1 + ::error:: 让失败可见
          # （旧实现 rebase 失败后 exit 0 = 静默成功，job 仍显示绿勾）。
          # continue-on-error: true 确保失败不阻断后续部署步骤。
          git pull --rebase --autostash origin main || {
            echo "::error title=Rebase 冲突::quality data commit 无法 rebase，请人工介入"
            git rebase --abort 2>/dev/null || true
            exit 1
          }
          git push origin main || {
            echo "::error title=Push 失败::quality data 已 commit 但 push 被拒（多个机器人每 ~30 分钟提交，push 被拒是常态）"
            exit 1
          }
```

**为什么这样改**：
- 旧实现 `exit 0` 让 rebase/push 失败后 step 仍成功，job 显示绿勾——这是「静默成功」，比失败更危险（GSC 数据停滞 30 天但 status=OK 是同一类问题）。
- 改为 `exit 1` + `::error::` 让失败可见（step 显示红色 X，日志里有红色 `::error::` 行）。
- 加 `continue-on-error: true` 确保失败不阻断后续部署步骤（pre-deploy gate → post-build validation → deploy to Cloudflare Pages）。quality data 是「nice to have」——publish 失败不应阻断部署。
- 注意：pre-deploy quality gate（L65-69 `--fail-on P1`）未被降级，保持原样。

### 2.2 "Commit social manifest back to repo" step（原 L125-136 → 新 L136-158）

**改前**：
```yaml
      - name: Commit social manifest back to repo
        if: always()
        run: |
          ...
              git pull --rebase origin main || echo "rebase had conflicts"
              git push origin main || echo "manifest push failed (non-fatal)"
```

**改后**（关键行）：
```yaml
      - name: Commit social manifest back to repo
        if: always()
        continue-on-error: true
        run: |
          ...
            git commit -m "chore: sync social publish manifest" && {
              # 补 --autostash（旧实现缺此项，会导致与 quality-monitor 同款的
              # unstaged changes rebase 失败）。exit 0 → exit 1 + ::error:: 让
              # 失败可见；continue-on-error: true 确保不阻断后续步骤。
              git pull --rebase --autostash origin main || {
                echo "::error title=Rebase 冲突::manifest commit 无法 rebase，请人工介入"
                git rebase --abort 2>/dev/null || true
                exit 1
              }
              git push origin main || {
                echo "::error title=Push 失败::manifest 已 commit 但 push 被拒"
                exit 1
              }
            }
```

**为什么这样改**：
- 旧实现 `git pull --rebase` 无 `--autostash`，与搞挂 Quality Monitor 的根因完全相同（unstaged changes 导致 rebase 失败）。
- `echo "rebase had conflicts"` 和 `echo "manifest push failed (non-fatal)"` 是静默失败——step 成功，job 绿勾，但 manifest 没提交。
- 加 `--autostash` + `exit 1` + `::error::` + `continue-on-error: true`。

### 2.3 "Commit brand identity audit report back to repo" step（原 L138-158 → 新 L160-191）

**改前**：
```yaml
      - name: Commit brand identity audit report back to repo
        if: always()
        run: |
          ...
          git pull --rebase --autostash origin main || { git rebase --abort 2>/dev/null || true; echo "rebase failed"; exit 0; }
          git push origin main || echo "brand report push failed (non-fatal)"
```

**改后**（关键行）：
```yaml
      - name: Commit brand identity audit report back to repo
        if: always()
        continue-on-error: true
        run: |
          ...
          git commit -m "chore(brand): publish brand identity audit [skip ci]"
          # --autostash 已存在；把 exit 0 改为 exit 1 + ::error:: 让失败可见
          # （旧实现 rebase 失败后 exit 0 = 静默成功，job 仍显示绿勾）。
          # continue-on-error: true 确保失败不阻断后续步骤。
          git pull --rebase --autostash origin main || {
            echo "::error title=Rebase 冲突::brand audit commit 无法 rebase，请人工介入"
            git rebase --abort 2>/dev/null || true
            exit 1
          }
          git push origin main || {
            echo "::error title=Push 失败::brand audit 已 commit 但 push 被拒"
            exit 1
          }
```

**为什么这样改**：
- 同 2.1。`exit 0` → `exit 1` + `::error::` + `continue-on-error: true`。
- 这个 step 的注释（原 L143-149）已经记录了「静默假绿灯」的危害：品牌审计报告显示 0-FAIL 但实际未刷新 18 天，agent_kpi_auditor.py 据此给出 100% 品牌一致性。本次修复让 rebase/push 失败可见，减少这类静默失败。

---

## 3. 本地静态校验结果

### 3.1 YAML 语法

```
python -c "import yaml,pathlib,sys; fs=['.github/workflows/ops-dashboard-hourly.yml','.github/workflows/deploy-cloudflare-pages.yml']; [yaml.safe_load(pathlib.Path(f).read_text(encoding='utf-8')) for f in fs]; print('yaml ok:', fs)"
```

**结果**：`yaml ok: ['.github/workflows/ops-dashboard-hourly.yml', '.github/workflows/deploy-cloudflare-pages.yml']`（exit 0）

### 3.2 `git pull --rebase` 无 `--autostash` 扫描

```
python -c "import pathlib,sys,re; bad=[]; [bad.append((f,i,l.strip())) for f in ['.github/workflows/ops-dashboard-hourly.yml','.github/workflows/deploy-cloudflare-pages.yml'] for i,l in enumerate(pathlib.Path(f).read_text(encoding='utf-8').splitlines(),1) if re.search(r'git\s+pull\s+--rebase', l) and '--autostash' not in l]; print('pull --rebase without --autostash:', bad); sys.exit(1 if bad else 0)"
```

**结果**：`pull --rebase without --autostash: []`（exit 0，两个文件中所有 `git pull --rebase` 调用都已含 `--autostash`）

### 3.3 `git pull --rebase --autostash` 存在性

```
python -c "import pathlib,sys; h=pathlib.Path('.github/workflows/ops-dashboard-hourly.yml').read_text(encoding='utf-8'); d=pathlib.Path('.github/workflows/deploy-cloudflare-pages.yml').read_text(encoding='utf-8'); miss=[x for x in ['git pull --rebase --autostash'] if x not in h or x not in d]; print('missing autostash rebase:', miss); sys.exit(1 if miss else 0)"
```

**结果**：`missing autostash rebase: []`（exit 0）

### 3.4 补充断言

| 断言 | 结果 |
|---|---|
| ops-dashboard-hourly.yml：1 个 push，1 个 preceding rebase | ✅ |
| deploy-cloudflare-pages.yml：3 个 push，3 个 preceding rebases | ✅ |
| deploy-cloudflare-pages.yml：所有 rebases 含 `--autostash` | ✅ |
| `continue-on-error: true` 出现在 quality data / manifest / brand audit 三个 step | ✅ |
| pre-deploy quality gate 未被降级（`predeploy_quality_gate.py --fail-on P1` 存在） | ✅ |
| 不存在 `exit 0` 跟随 rebase 失败的情况 | ✅ |

---

## 4. t5 疑问核实：`reports/site_health/` 目录

**t5 疑问**：路径白名单含 `reports/site_health/`，但 `site_health_agent.py` 实际输出到 `reports/daily_issues/`。若 `reports/site_health/` 一直为空，`git add` 对该路径无操作（harmless），但 Upload Reports 引用该目录会上传空目录。

**核实结论**：t5 的疑问是误报。`site_health_agent.py` **同时**写两个目录：

| 目录 | 来源 | 文件 |
|---|---|---|
| `reports/site_health/` | L44 `REPORTS_DIR = ROOT / "reports" / "site_health"`；L1426 `report_file = REPORTS_DIR / f"site_health_{date}.json"` | `site_health_YYYY-MM-DD.json`（完整健康检查报告） |
| `reports/daily_issues/` | L45 `ISSUES_DIR = ROOT / "reports" / "daily_issues"`；L1433 `issues_file = ISSUES_DIR / f"site_health_issues_{date}.json"` | `site_health_issues_YYYY-MM-DD.json`（未修复问题，供 router 分配） |

**结论**：`reports/site_health/` 不会被 `site_health_agent.py` 写空。每次运行都产出 `site_health_YYYY-MM-DD.json`。Upload Reports step 引用该目录不会上传空目录。t5 的疑问无需处理。

---

## 5. 需要 GitHub Actions 实跑才能最终确认的事项

| # | 待确认项 | 验证方法 | 风险等级 |
|---|---|---|---|
| 1 | ops-dashboard-hourly.yml 的 `git pull --rebase --autostash` 在 CI 环境正常工作 | 等下次 cron 触发（`*/30 1-18 * * *` UTC），看 step 日志是否 rebase 成功 | 低 |
| 2 | deploy-cloudflare-pages.yml manifest commit step 的 `--autostash` 不再因 unstaged changes 失败 | 触发一次 workflow_dispatch，看 manifest step 日志 | 低 |
| 3 | `continue-on-error: true` + `exit 1` 让失败可见（step 显示红色 X，job 仍绿勾） | 看 workflow run 的 step 状态 | 低 |
| 4 | `::error::` annotation 在 CI 日志中正确显示 | 触发一次 workflow_dispatch，看日志 | 低 |
| 5 | quality data / manifest / brand audit commit 失败不阻断部署 | 看 workflow run 的 deploy step 是否在 commit step 失败后仍运行 | 低 |
| 6 | 三个 commit step 的 push 在并发提交下不被拒（或失败时有可读告警） | 等自然 cron 触发 | 中 |

---

## 6. 遗留问题 / 风险

1. **`continue-on-error: true` 的副作用**：三个 step 加 `continue-on-error: true` 后，step 失败不会让 job conclusion 变红。失败只在 step 详情里可见（红色 X + `::error::` 日志）。如果团队依赖 job conclusion 做告警（例如 retry-failed.yml 按 `conclusion == 'failure'` 触发），这些 step 的失败不会被重试。这是**期望行为**——这些 step 是 post-deploy commit，失败重试只是重复 commit 同内容（idempotent），且 push 被拒的根因（并发提交）重试也大概率还是被拒。

2. **ops-dashboard-hourly.yml 的 `gh workflow run` 在 push 失败后不执行**：push 失败时 `exit 1`，`gh workflow run "Post-deploy Tasks"` 不会执行。但 push 本身已触发 deploy（`on: push paths: [static/**]` 匹配 static/ops-dashboard/ 与 static/ops/），所以 `gh workflow run` 是冗余触发器。如果未来 deploy 的 paths filter 变了（例如移除了 `static/**`），这个冗余触发器可能会成为唯一触发器。建议后续确认 paths filter 不变。

3. **未统一 ops-dashboard-hourly.yml 的 `continue-on-error`**：ops-dashboard-hourly.yml 的 push 失败后 `exit 1` 但没有加 `continue-on-error: true`，所以 step 失败会让 job 失败。这是**期望行为**——ops-dashboard 刷新失败应该是可见的（不像 deploy-cloudflare-pages.yml 的 post-deploy commit 那样是 nice-to-have）。

---

## 7. 验收对照

| 验收项 | 状态 | 证据 |
|---|---|---|
| ops-dashboard-hourly.yml push 前补 `git pull --rebase --autostash` | ✅ passed | L91 `git pull --rebase --autostash origin main`；verify 命令确认存在 |
| deploy-cloudflare-pages.yml L133 补 `--autostash` | ✅ passed | L148 `git pull --rebase --autostash origin main`；扫描确认无 `git pull --rebase` 缺 `--autostash` |
| deploy-cloudflare-pages.yml L91/L157 exit 0 → exit 1 + ::error:: + continue-on-error | ✅ passed | L81/L138/L162 三个 step 加 `continue-on-error: true`；L95-99/L148-151/L183-186 rebase 失败后 `exit 1` + `::error::`；L100-102/L153-155/L188-190 push 失败后 `exit 1` + `::error::` |
| 两个 workflow YAML 语法有效 | ✅ passed | `yaml.safe_load` 通过 2 个文件 |
| 扫描确认无 `git pull --rebase` 缺 `--autostash` | ✅ passed | verify 命令输出 `pull --rebase without --autostash: []` |
| 扫描确认无 `git push` 前无 rebase | ✅ passed | ops-dashboard-hourly.yml 1 push / 1 rebase；deploy-cloudflare-pages.yml 3 pushes / 3 rebases |
| t5 疑问核实 | ✅ passed | `site_health_agent.py` 同时写 `reports/site_health/`（L1426）和 `reports/daily_issues/`（L1433），`reports/site_health/` 不会被写空 |
| pre-deploy quality gate 未降级 | ✅ passed | `predeploy_quality_gate.py --fail-on P1` 仍在 L68 |
| reports/ci_reliability_followup_2026-09-21.md 交付 | ✅ passed | 本文件 |
