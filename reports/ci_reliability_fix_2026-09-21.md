# CI 闭环可靠性修复报告 · 2026-09-21

**修复对象**：`.github/workflows/quality-monitor.yml` + `.github/workflows/site-health-daily.yml`
**修复人**：ci-reliability（AgentTeams · chinabound-prod-hardening · t5）
**依赖分诊**：`reports/chatgpt_triage_2026-09-21.md`（P0-4 / P0-5 CI 闭环缺陷）
**本地 HEAD**：以 `git pull --rebase` 后为准（本仓库多个机器人每 ~30 分钟向 main 提交）
**约束**：未触发任何部署 / push；仅改 YAML + 写本报告

---

## 0. 修复摘要

| 问题 | 根因 | 修法 |
|---|---|---|
| P0-4 Quality Monitor 闭环断在 commit | `git pull --rebase origin main`（无 `--autostash`）遇到工作区残留（审计脚本写到 `reports/quality/`、`reports/daily_issues/` 之外的目录）以 `cannot pull with rebase: You have unstaged changes` 失败，整条「发现→报警→写报告→commit→push」链在最后一步挂 | 改为 `git pull --rebase --autostash origin main`，并在 rebase / push 失败时给 `::error::` 可读告警 |
| P0-5 Site Health 假绿灯（a） | `DASH_FAIL` 只打 `::warning::` 后继续，job conclusion 仍 SUCCESS → 出现「Workflow=SUCCESS 但看板没刷新」 | 把 `::warning::` 升级为 `::error::`，并让 step 在 `DASH_FAIL != 0` 时 `exit 1`；同时写 `GITHUB_STEP_SUMMARY` + `GITHUB_OUTPUT` 留痕 |
| P0-5 Site Health 假绿灯（b） | `cp ops-dashboard/index.html static/ops-dashboard/index.html` 无条件执行；`build.py` 失败时仍把旧/半成品文件覆盖上线 | 把 `cp` 放进 `if [ "$DASH_FAIL" = "0" ]` 条件内；失败分支明确 skip publish |
| P0-5 Site Health 假绿灯（c） | `git add -A` 会把工作区任何残留（含临时脚本、pytest 副作用产物）顺手提交上线；push 前完全没有 `git pull --rebase` | 改为按路径限定 `git add reports/site_health/ reports/daily_issues/ reports/closed_loop_audit/ reports/quality/ static/ops-dashboard/ static/ops/`；push 前加 `git pull --rebase --autostash`；rebase / push 失败时给 `::error::` 可读告警 |

---

## 1. quality-monitor.yml 改动详情

**改动范围**：L122-134（原）→ L122-146（新），+12 行。

**改前**：
```yaml
      - name: Commit quality reports
        if: always()
        run: |
          ...
          git commit -m "chore(quality): refresh website audit reports [skip ci]"
          git pull --rebase origin main
          git push origin main
```

**改后**（关键行）：
```yaml
          git commit -m "chore(quality): refresh website audit reports [skip ci]"
          # --autostash: 审计脚本会写到 reports/quality/ 与 reports/daily_issues/
          # 之外的目录（例如 ops-dashboard/、static/ops/、reports/site_health/），
          # 那些改动会留在工作区；`git pull --rebase` 遇到 unstaged changes 会以
          # "cannot pull with rebase: You have unstaged changes" 失败，
          # 整个「发现→报警→写报告→commit→push」闭环断在最后一步。
          git pull --rebase --autostash origin main || {
            echo "::error title=Rebase 冲突::quality report commit 无法 rebase，请人工介入"
            git rebase --abort 2>/dev/null || true
            exit 1
          }
          git push origin main || {
            echo "::error title=Push 失败::quality reports 已 commit 但 push 被拒（多个机器人每 ~30 分钟提交，push 被拒是常态）"
            exit 1
          }
```

**为什么这样改**：
- `--autostash` 让 git 在 rebase 前自动 stash 工作区残留、rebase 后自动恢复，直接消除「unstaged changes 导致 rebase 失败」的根因。
- `|| { echo "::error ..."; exit 1; }` 让 rebase / push 失败时给出可读告警（GitHub Actions 日志里会显示红色 `::error::` 行），而不是静默失败。
- `git rebase --abort 2>/dev/null || true` 在 rebase 失败时尝试清理 rebase 状态，避免留下残留状态影响后续操作（即使清理失败也无害）。

**设计偏差**：无。修法与 captain 建议一致。

---

## 2. site-health-daily.yml 改动详情

**改动范围**：L93-130（原）→ L93-169（新），+39 行。

### 2.1 (5/6) Regenerate Dashboard 步骤

**改前**：
```yaml
      - name: (5/6) Regenerate Dashboard (看板更新)
        if: success()
        run: |
          echo "Regenerating ops dashboard..."
          DASH_FAIL=0
          if ! python ops-dashboard/collect_data.py; then
            DASH_FAIL=1
            echo "::warning title=看板数据生成失败::ops-dashboard/collect_data.py 退出非零，本次流水线不阻断，但数据可能仍是旧值"
          fi
          if ! python ops-dashboard/build.py; then
            DASH_FAIL=1
            echo "::warning title=看板页面构建失败::ops-dashboard/build.py 退出非零，本次流水线不阻断，但 static/ops-dashboard/index.html 可能未更新"
          fi
          cp ops-dashboard/index.html static/ops-dashboard/index.html
          cp ops-dashboard/dashboard_data.json static/ops-dashboard/dashboard_data.json
          echo "Dashboard regenerated (script_failures=${DASH_FAIL})"
          {
            echo "### Regenerate Dashboard"
            if [ "$DASH_FAIL" = "1" ]; then
              echo "- ❌ collect_data.py 和/或 build.py 退出非零。流水线按设计继续（保持原有容错），"
              echo "  但看板数据可能未刷新。请查看本 step 日志定位具体脚本。"
            else
              echo "- ✅ collect_data.py / build.py 均退出 0"
            fi
          } >> "$GITHUB_STEP_SUMMARY"
```

**改后**（关键行）：
```yaml
      - name: (5/6) Regenerate Dashboard (看板更新)
        if: success()
        id: dashboard
        run: |
          echo "Regenerating ops dashboard..."
          DASH_FAIL=0
          if ! python ops-dashboard/collect_data.py; then
            DASH_FAIL=1
            echo "::error title=看板数据生成失败::ops-dashboard/collect_data.py 退出非零，本次不会把旧/半成品看板发布上线"
          fi
          if ! python ops-dashboard/build.py; then
            DASH_FAIL=1
            echo "::error title=看板页面构建失败::ops-dashboard/build.py 退出非零，本次不会把旧/半成品看板发布上线"
          fi
          # 只有构建成功时才发布到 static/ops-dashboard/。
          # 旧实现无条件 cp，build.py 失败时会把旧/半成品文件覆盖到
          # static/ops-dashboard/index.html 与 dashboard_data.json，
          # 等于把陈旧数据发布上线。
          if [ "$DASH_FAIL" = "0" ]; then
            cp ops-dashboard/index.html static/ops-dashboard/index.html
            cp ops-dashboard/dashboard_data.json static/ops-dashboard/dashboard_data.json
            echo "Dashboard regenerated and published"
          else
            echo "Dashboard build failed — skipping publish to static/ops-dashboard/ to avoid publishing stale/partial data"
          fi
          {
            echo "### Regenerate Dashboard"
            if [ "$DASH_FAIL" = "0" ]; then
              echo "- ✅ collect_data.py / build.py 均退出 0；index.html 与 dashboard_data.json 已同步到 static/ops-dashboard/"
            else
              echo "- ❌ collect_data.py 和/或 build.py 退出非零"
              echo "- ❌ 未把 ops-dashboard/index.html 或 dashboard_data.json 复制到 static/ops-dashboard/（避免发布陈旧/半成品数据）"
              echo "- 请查看本 step 日志定位具体脚本；本 step 将 exit 1 让 job 可见失败（消除「Workflow=SUCCESS 但看板没刷新」假绿灯）"
            fi
          } >> "$GITHUB_STEP_SUMMARY"
          echo "dashboard_fail=$DASH_FAIL" >> "$GITHUB_OUTPUT"
          # 假绿灯修复：DASH_FAIL != 0 时让 step 失败，job conclusion = failed，
          # 不再只 echo warning 后继续。
          if [ "$DASH_FAIL" != "0" ]; then
            exit 1
          fi
```

**为什么这样改**：
- `::warning::` → `::error::`：GitHub Actions 日志里红色标注，一眼能看出是错误不是警告。
- `if [ "$DASH_FAIL" = "0" ]` 包住 `cp`：只有构建成功时才发布到 `static/ops-dashboard/`，失败时明确 skip，不发布陈旧/半成品数据。
- `exit 1` 在 `DASH_FAIL != 0` 时让 step 失败，job conclusion = failed（GitHub Actions UI 上显示红色 X），消除「Workflow=SUCCESS 但看板没刷新」假绿灯。
- `GITHUB_STEP_SUMMARY`：写明确的 job summary，无论成功失败都留痕。
- `GITHUB_OUTPUT` + `id: dashboard`：把 `dashboard_fail` 暴露给后续 step（虽然当前没有 step 依赖它，但留了扩展点）。

**设计偏差**：
- 原设计「DASH_FAIL 只打 warning 后继续」是有意容错，注释写「本次流水线不阻断」。本次修复把容错改为阻断（`exit 1`），因为「假绿灯」比「阻断」更危险——假绿灯会让所有人以为看板是新的，实际是旧的。
- 修复后如果 dashboard 构建失败，job 会变红。这是**期望行为**：dashboard 构建失败本来就该被发现，而不是被静默吞掉。
- 副作用：`(6/6) Commit & Push` 步骤从 `if: success()` 改为 `if: always()`（见 2.2），确保即使 dashboard step 失败，前序步骤产生的 reports 仍能 commit。

### 2.2 (6/6) Commit & Push 步骤

**改前**：
```yaml
      - name: (6/6) Commit & Push (提交)
        if: success()
        run: |
          git config --local user.email "ai-agent@chinaboundtravel.com"
          git config --local user.name "Closed Loop Agent"
          git add -A
          if git diff --cached --quiet; then
            echo "No changes to commit"
          else
            git commit -m "fix(closed-loop): auto detect→assign→execute→audit by Site Health Agent [skip ci]"
            git push origin main
          fi
```

**改后**（关键行）：
```yaml
      - name: (6/6) Commit & Push (提交)
        if: always()
        run: |
          git config --local user.email "ai-agent@chinaboundtravel.com"
          git config --local user.name "Closed Loop Agent"
          # 按路径限定 add（替代旧的 git add -A）。
          # AGENTS.md 明说 site-health-daily 的 git add -A 会把工作区任何残留
          # （含临时脚本、pytest 副作用产物）顺手提交上线。改为只 add 本 workflow
          # 实际产出目录，收敛风险面。
          # 注意：不 add ops-dashboard/（build.py 失败时的半成品产物会被留在
          # 工作区，下次 workflow 会重新生成），也不 add content/、static/_redirects
          # 等手工维护区。
          git add \
            reports/site_health/ \
            reports/daily_issues/ \
            reports/closed_loop_audit/ \
            reports/quality/ \
            static/ops-dashboard/ \
            static/ops/
          if git diff --cached --quiet; then
            echo "No changes to commit"
          else
            git commit -m "fix(closed-loop): auto detect→assign→execute→audit by Site Health Agent [skip ci]"
            # push 前必须 rebase：多个机器人每 ~30 分钟向 main 提交，push 被拒
            # 是常态（见 AGENTS.md "自动化并发纪律"）。--autostash 处理工作区残留。
            git pull --rebase --autostash origin main || {
              echo "::error title=Rebase 冲突::site-health 提交无法 rebase，请人工介入"
              git rebase --abort 2>/dev/null || true
              exit 1
            }
            git push origin main || {
              echo "::error title=Push 失败::site-health 提交已 commit 但 push 被拒（其他机器人可能同时提交）"
              exit 1
            }
          fi
```

**为什么这样改**：
- `if: always()`：dashboard step 失败（`exit 1`）后，job 已经 conclusion=failed，但前序步骤（site_health_agent / daily_issue_router / agent_task_executor / closed_loop_audit）产生的 reports 仍应 commit，否则这些数据要等到下次 workflow 才上线。`always()` 让 commit step 在 job 失败时仍运行。
- `git add` 按路径限定：收敛 AGENTS.md 明说的「`git add -A` 会把工作区任何残留顺手提交上线」风险面。只 add 本 workflow 实际产出的 6 个目录。
- `git pull --rebase --autostash origin main`：补上 push 前的 rebase。本仓库多个机器人每 ~30 分钟提交，push 被拒是常态（AGENTS.md 明说 2026-09-16 一小时内被拒 2 次）。`--autostash` 处理工作区残留（虽然前一步已经 `exit 1` 了，但 commit step 的 `git add` 可能把新文件加进来，rebase 前需要干净工作区）。
- rebase / push 失败时给 `::error::` 可读告警。

**路径白名单说明**：
| 路径 | 来源 | 说明 |
|---|---|---|
| `reports/site_health/` | site_health_agent.py | 健康检查结果 |
| `reports/daily_issues/` | daily_issue_router.py | 每日问题路由 |
| `reports/closed_loop_audit/` | closed_loop_audit.py | 闭环审计报告 |
| `reports/quality/` | merge_quality_issues.py | 质量报告合并 |
| `static/ops-dashboard/` | (5/6) step 的 cp | 看板发布产物（仅构建成功时） |
| `static/ops/` | (5/6) step 的 cp 或 ops-dashboard-hourly | /ops/ 目录产物 |

**不在白名单**（不 add，留在工作区等下次）：
- `ops-dashboard/`（build.py 失败时的半成品产物，下次 workflow 会重新生成）
- `content/`、`static/_redirects`、`ops-dashboard/ops-center.html`（手工维护区）
- 任何临时脚本（AGENTS.md 要求用完即删）

---

## 3. 本地静态校验结果

### 3.1 YAML 语法

```
python -c "import yaml,pathlib,sys; fs=['.github/workflows/quality-monitor.yml','.github/workflows/site-health-daily.yml','.github/workflows/ops-dashboard-hourly.yml']; [yaml.safe_load(pathlib.Path(f).read_text(encoding='utf-8')) for f in fs]; print('yaml ok:', fs)"
```

**结果**：`yaml ok: ['.github/workflows/quality-monitor.yml', '.github/workflows/site-health-daily.yml', '.github/workflows/ops-dashboard-hourly.yml']`（exit 0）

### 3.2 关键内容断言

```
python -c "import pathlib,sys; t=pathlib.Path('.github/workflows/quality-monitor.yml').read_text(encoding='utf-8'); miss=[x for x in ['--autostash'] if x not in t]; print('missing:', miss); sys.exit(1 if miss else 0)"
```

**结果**：`missing: []`（exit 0，quality-monitor.yml 含 `--autostash`）

```
python -c "import pathlib,sys; t=pathlib.Path('.github/workflows/site-health-daily.yml').read_text(encoding='utf-8'); miss=[x for x in ['git pull --rebase'] if x not in t]; print('missing pre-push rebase:', miss); sys.exit(1 if miss else 0)"
```

**结果**：`missing pre-push rebase: []`（exit 0，site-health-daily.yml 含 `git pull --rebase`）

### 3.3 补充断言（逻辑评审）

| 断言 | 结果 |
|---|---|
| `git add -A` 作为实际命令（非注释） | 不存在 ✅ |
| `--autostash` 出现次数 ≥ 1 | 2 次 ✅ |
| `exit 1` 出现次数 ≥ 1 | 4 次 ✅ |
| `GITHUB_STEP_SUMMARY` 写入 | 存在 ✅ |
| `GITHUB_OUTPUT` 写入 | 存在 ✅ |
| `if [ "$DASH_FAIL" = "0" ]` 条件包住 cp | 存在 ✅ |
| `id: dashboard` step id | 存在 ✅ |
| `if: always()` 在 commit step | 存在 ✅ |
| 路径白名单含 `reports/site_health/` | 存在 ✅ |
| 路径白名单含 `static/ops-dashboard/` | 存在 ✅ |

---

## 4. 需要 GitHub Actions 实跑才能最终确认的事项

本地无法验证 GitHub Actions 运行时行为，以下项需要至少一次 workflow 实跑确认：

| # | 待确认项 | 验证方法 | 风险等级 |
|---|---|---|---|
| 1 | `git pull --rebase --autostash` 在 CI 环境（ubuntu-22.04）上正常工作 | 等 quality-monitor 或 site-health-daily 下次 cron 触发，看 step 日志是否 rebase 成功 | 低（标准 git 选项，GitHub Actions 环境已支持多年） |
| 2 | `::error::` annotation 在 CI 日志中正确显示 | 触发一次 workflow_dispatch，看日志是否有红色 `::error::` 行 | 低（标准 GitHub Actions 语法） |
| 3 | `exit 1` 让 job conclusion = failed（红色 X） | 让 dashboard step 失败一次（例如临时移除一个依赖文件），看 job conclusion | 低（标准 shell 行为） |
| 4 | `if: always()` 让 commit step 在 job 失败时仍运行 | 同上，看 commit step 是否在 dashboard step 失败后仍执行 | 低（标准 GitHub Actions 语法） |
| 5 | 路径白名单 `git add` 不会漏掉实际产出文件 | 看 commit step 的 `git diff --cached --stat` 输出，确认只 stage 了白名单内的文件 | 中（如果某脚本产出的目录不在白名单内，会被静默漏掉） |
| 6 | `GITHUB_STEP_SUMMARY` 在 GitHub UI 上正确显示 | 看 workflow run 的 Summary tab | 低（标准 GitHub Actions 语法） |
| 7 | `GITHUB_OUTPUT` + `id: dashboard` 正确暴露 `dashboard_fail` 变量 | 加一个调试 step `echo ${{ steps.dashboard.outputs.dashboard_fail }}` 看输出 | 低（标准 GitHub Actions 语法） |
| 8 | `git push` 在并发提交下不被拒（或失败时有可读告警） | 等 quality-monitor 下次 cron 触发，看 push step 日志 | 中（依赖并发提交频率，push 被拒后本 workflow 不会重试，需下次 cron 再来） |

**建议**：本次修复合并后，触发一次 `workflow_dispatch`（site-health-daily 支持手动触发），看完整日志确认上述 1-7 项。第 8 项等自然 cron 触发即可。

---

## 5. 未修复的同类问题（建议后续处理）

本次任务 in-scope 包含 `.github/workflows/ops-dashboard-hourly.yml` 与 `.github/workflows/deploy-cloudflare-pages.yml`，但 acceptance criteria 只明确要求修 quality-monitor.yml 与 site-health-daily.yml。为控制变更面，本次未修改这两个文件。同类问题清单：

| 文件 | 行号 | 问题 | 建议 |
|---|---|---|---|
| `ops-dashboard-hourly.yml` | L89 | `git push origin main` 前无 `git pull --rebase` | 加 `git pull --rebase --autostash origin main` |
| `deploy-cloudflare-pages.yml` | L133 | `git pull --rebase origin main` 无 `--autostash`（manifest commit step） | 加 `--autostash` |
| `deploy-cloudflare-pages.yml` | L91, L157 | 已有 `--autostash`（quality dashboard + brand audit step），但失败后 `exit 0` 吞掉错误 | 改为 `exit 1` 让 job 可见失败，或至少在 summary 里留痕 |

**说明**：这些是同类缺陷，但不在本次 acceptance 范围内。建议单独开一个 task 统一处理，避免本次变更面过大。

---

## 6. 遗留问题 / 风险

1. **`reports/site_health/` 目录可能为空**：本次路径白名单包含 `reports/site_health/`，但 site-health-daily.yml 的 step (1/6) 调用 `site_health_agent.py` 时，实际输出目录是 `reports/daily_issues/`（L66）。如果 `reports/site_health/` 一直为空，`git add` 对该路径无操作（harmless），但 Upload Reports step（L176）引用该目录会上传空目录。建议核实 `site_health_agent.py` 是否真的写 `reports/site_health/`，如果不写，从白名单移除（不影响本次修复）。

2. **dashboard 构建失败后 reports 仍 commit**：`if: always()` 让 commit step 在 dashboard step 失败后仍运行。这确保 reports 不丢，但也意味着「dashboard 构建失败 + reports 已 commit」的组合会出现。这是**期望行为**——reports 是前序步骤的真实产出，应该上线；dashboard 是本次构建失败，下次 workflow 会重新构建。

3. **push 失败不会重试**：本次修复让 push 失败时给出可读告警，但没有加重试逻辑。下次 cron 触发会重新跑整个 workflow，reports 会重新生成并 commit。如果 push 被拒是常态（AGENTS.md 说一小时内被拒 2 次），可能需要加重试逻辑（例如 `for i in 1 2 3; do git push || break; sleep $((RANDOM % 30 + 10)); done`）。但重试逻辑会引入 sleep，占用 CI 资源，建议先观察本次修复后的实际 push 成功率再决定。

4. **`--autostash` 与 pytest 副作用的交互**：AGENTS.md 明说「pytest 有写副作用，跑全量 pytest 会改写 reports/revenue/*、reports/seo/*、static/lead-magnet/*.pdf 共 12 个 Protected Area 文件」。如果 site-health-daily 或 quality-monitor 在 CI 上跑 pytest（当前没有，但未来可能加），`--autostash` 会把 pytest 产生的改动 stash 起来、rebase 后恢复，但 commit step 的 `git add` 是路径白名单，所以 pytest 产物不会被 commit。这是**期望行为**——pytest 产物是副作用，不应该被 commit。但如果未来想 commit pytest 产物，需要把它们加到白名单里。

---

## 7. 验收对照

| 验收项 | 状态 | 证据 |
|---|---|---|
| quality-monitor.yml commit 步骤不再因 unstaged changes 失败 | ✅ passed | L138 `git pull --rebase --autostash origin main`；verify 命令确认 `--autostash` 存在 |
| quality-monitor.yml push 失败时给出可读告警 | ✅ passed | L143-146 `git push origin main || { echo "::error title=Push 失败::..."; exit 1; }` |
| site-health-daily.yml DASH_FAIL 让 job 可见失败 | ✅ passed | L131-133 `if [ "$DASH_FAIL" != "0" ]; then exit 1; fi`；`::warning::` 升级为 `::error::`（L101, L105） |
| site-health-daily.yml 无条件 cp 修掉 | ✅ passed | L111-117 `if [ "$DASH_FAIL" = "0" ]; then cp ...; else echo "skipping publish"; fi` |
| site-health-daily.yml git add -A 风险收敛 | ✅ passed | L147-153 改为按路径限定 `git add \` 6 个目录；实际命令中 `git add -A` 不存在（仅在注释中出现） |
| site-health-daily.yml push 前加 git pull --rebase --autostash | ✅ passed | L160 `git pull --rebase --autostash origin main`；verify 命令确认 `git pull --rebase` 存在 |
| 所有改动的 workflow YAML 语法有效 | ✅ passed | `yaml.safe_load` 通过 3 个文件 |
| reports/ci_reliability_fix_2026-09-21.md 交付 | ✅ passed | 本文件 |
