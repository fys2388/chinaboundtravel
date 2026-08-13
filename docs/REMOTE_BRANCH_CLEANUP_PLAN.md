# REMOTE_BRANCH_CLEANUP_PLAN — trae 分支处理计划（仅供审核，未执行）

> 日期：2026-08-13 | 状态：PLAN ONLY，不删除任何 remote branch

| 分支 | 当前 tip | 含泄漏 | 含 P0–P0.6 | 需要删除 | 删除前备份 | 删除后验证 |
|---|---|---|---|---|---|---|
| origin/trae/solo-agent-fLtHYf | ced3f2e6 | 是（Buffer token ×3、.env/whsec、Feishu） | 否 | 是（泄漏+无价值） | `git fetch origin trae/solo-agent-fLtHYf:refs/backup/trae-fLtHYf`（本地保留）+ 已含在总 bundle | `git ls-remote origin` 确认分支消失；本地 backup ref 存在 |
| origin/trae/solo-agent-h8fIab | 99b7f3b2 | 是（同上） | 否 | 是 | 同上（refs/backup/trae-h8fIab） | 同上 |
| origin/trae/solo-agent-y3VxiW | f3440115 | 是（同上） | 否 | 是 | 同上（refs/backup/trae-y3VxiW） | 同上 |

## 说明
- 3 个分支均创建于泄漏清理前，tip 仍含真实凭据明文，且不含任何 P0–P0.6 修复 → 无保留价值。
- 备份：全局 bundle（_cbt_backup_20260813_144413）已包含全部 refs；另建议推送前在本地保存 `refs/backup/trae-*`。
- 删除命令（人工执行，需授权）：`git push origin --delete trae/solo-agent-fLtHYf`（×3）。
- 删除后：验证 `git ls-remote origin` 无 trae 分支；确认 GitHub 页面分支列表为空。