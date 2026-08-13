# FORCE_PUSH_PLAN — ChinaBound Travel Git 历史恢复推送计划（仅供审核，未执行）

> 日期：2026-08-13 | 状态：PLAN ONLY，任何 push 均需仓库所有者明确授权

## 当前状态
| 项 | 值 |
|---|---|
| local main（当前） | bd80020b（含 P0–P0.6 全部修复 + 安全恢复文档） |
| local main（重写后演练结果） | 2dcb595（同一 tree，新 hash；历史已清除 5 个真实凭据 + .env） |
| origin/main | 2e5bb7a（不含 P0–P0.6，历史仍含泄漏，tip 仍含 Buffer token 明文） |
| 分支关系 | 无共同祖先（两套独立血统） |

## 1. local main 是否包含 P0–P0.6
是。P0（persona/workflow/error-alert/stripe-idempotency/human-gate/content-id/affiliate）、P0.5（secret governance/brand audit）、P0.6（buffer persona/content_id/dedup/secret cleanup/migration docs）均已在 bd80020b 及重写后 2dcb595 中验证存在；重写后 pytest 51 passed、content_id PASS、hugo exit 0。

## 2. origin/main 是否包含旧泄漏
是。历史含真实 Buffer token ×3、Stripe webhook secret（.env）、Feishu webhook；tip（2e5bb7a）仍含 Buffer token 明文（buffer-worker/*.js 等 29 文件）。

## 3. force-with-lease 是否必要
**是**。本地与 origin/main 无共同祖先，普通 `git push` 必然被拒；必须使用 `git push --force-with-lease`。
**禁止使用 `git push --force`**（无保护）。

## 4. 推荐执行顺序
1. 完成 Secret Rotation（先新后旧，见 SECRET_ROTATION_EXECUTION_PLAN.md）——重写无法撤销已泄露值。
2. 人工审核重写演练结果（本阶段 2dcb595）；在本地 main 应用重写（fetch 临时 clone 或重新执行 filter-repo）。
3. 备份确认（bundle 已存在，见备份记录）。
4. 执行 push（见 §5 检查清单通过后）。
5. 推送后处理 trae 分支（REMOTE_BRANCH_CLEANUP_PLAN.md）。
6. 部署（PRODUCTION_DEPLOYMENT_PLAN.md）。

## 5. force push 前最后检查
- [ ] `git status --short` 干净（无未提交 P0.6 变更）
- [ ] 本地 main 与演练重写结果 tree 一致（`git diff bd80020b 2dcb595 --stat` 为空或仅为预期差异）
- [ ] 重写后历史 secret pickaxe = 0（本阶段已验证 5/5 值 0 残留、.env 0 commits）
- [ ] 所有协作者已同步/无未推送 commit（`git log origin/main..main` 仅含预期重写内容）
- [ ] Secret 轮换已全部完成（否则泄露值仍有效）
- [ ] 仓库所有者授权确认（书面）

## 6. force push 后验证
- `git fetch origin && git rev-parse origin/main` == 本地重写 main
- `git log --oneline origin/main | head` 新历史
- 远程 tip secret 扫描（git grep）为 0
- GitHub Actions 新 main 触发一次 deploy 正常

## 7. rollback 方法
- 备份：`E:\AI\dulizhan\_cbt_backup_20260813_144413\chinaboundtravel-all.bundle`（旧历史完整备份，含全部 refs）
- 恢复：`git clone backup.bundle` 或 `git fetch <bundle> '+refs/*:refs/*'` 后 `git reset --hard` 到 2e5bb7a（旧 main）
- 注意：备份 bundle 内含旧泄漏历史，须离线/加密保管。