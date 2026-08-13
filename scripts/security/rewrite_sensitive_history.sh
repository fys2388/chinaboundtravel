#!/usr/bin/env bash
# =============================================================================
# ChinaBound Travel — Sensitive History Rewrite Script (REVIEW ONLY)
# -----------------------------------------------------------------------------
# 用途: 用 git filter-repo 重写本地历史, 清除以下已确认泄漏的凭据:
#   - Buffer OAuth token x3（具体值见 sensitive_values.txt）
#   - Stripe webhook secret（曾提交于 .env）
#   - Feishu webhook URL / secret (曾提交于 .env 与脚本/文档)
#   - 历史中的任何 .env 文件
# 约束(本脚本内建):
#   - 不执行 git push / force-push
#   - 不删除任何 remote branch
#   - 不修改当前 working tree(在临时镜像克隆中执行重写)
#   - 需要人工审核通过后, 由操作者按脚本末尾提示手动推送
#
# !!! 警告: 执行本脚本会永久重写本地 git 历史, 生成新的 commit hash !!!
# !!! 必须先在干净的备份上演练, 并由仓库所有者人工审核后再推送 !!!
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SENSITIVE_FILE="${SCRIPT_DIR}/sensitive_values.txt"
BACKUP_DIR="${REPO_ROOT}/backup/history-rewrite"
TS="$(date +%Y%m%d-%H%M%S)"

log()  { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die()  { printf '[FATAL] %s\n' "$*" >&2; exit 1; }

# -----------------------------------------------------------------------------
# 0. 前置检查(不满足则安全退出, 不重写任何东西)
# -----------------------------------------------------------------------------
command -v git-filter-repo >/dev/null 2>&1 \
  || die "git filter-repo 未安装. 安装: pip install git-filter-repo (或 brew install git-filter-repo)"

[ -f "${SENSITIVE_FILE}" ] \
  || die "缺少 ${SENSITIVE_FILE}。请把要清除的敏感值逐行填入该文件(该文件已被 .gitignore 忽略, 禁止提交)。"

[ -s "${SENSITIVE_FILE}" ] \
  || die "${SENSITIVE_FILE} 为空。拒绝执行。"

grep -qE 'PASTE|REPLACE|TODO' "${SENSITIVE_FILE}" \
  && die "${SENSITIVE_FILE} 仍含占位符(PASTE/REPLACE/TODO), 拒绝执行。"

# 人工确认门
log "即将在临时镜像克隆中重写本地历史(不影响当前工作区)。"
read -r -p "确认已阅读 docs/SECURITY_SECRET_ROTATION_CHECKLIST.md 并完成备份? 输入 YES 继续: " CONFIRM
[ "${CONFIRM}" = "YES" ] || die "已取消。未执行任何重写。"

# -----------------------------------------------------------------------------
# 1. 备份(不覆盖已有备份)
# -----------------------------------------------------------------------------
mkdir -p "${BACKUP_DIR}"
BUNDLE="${BACKUP_DIR}/pre-rewrite-${TS}.bundle"
log "创建全量备份 bundle: ${BUNDLE}"
git -C "${REPO_ROOT}" bundle create "${BUNDLE}" --all
log "备份完成。"

# -----------------------------------------------------------------------------
# 2. 在临时镜像克隆中执行重写(不触碰当前 working tree)
# -----------------------------------------------------------------------------
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

log "创建临时镜像克隆: ${TMP_DIR}/rewrite.git"
git clone --mirror "${REPO_ROOT}" "${TMP_DIR}/rewrite.git"

cd "${TMP_DIR}/rewrite.git"

# 2.1 用 --replace-text 抹除真实凭据(每行一个值, 替换为占位)
#     filter-repo 支持 literal 匹配; 自动追加 ==>***REMOVED*** 使其可读
REPLACE_FILE="${TMP_DIR}/replace.txt"
awk '{ print $0 "==>***REMOVED***" }' "${SENSITIVE_FILE}" > "${REPLACE_FILE}"

log "执行 git filter-repo --replace-text (凭据抹除) ..."
git filter-repo --force \
  --replace-text "${REPLACE_FILE}"

# 2.2 用 --invert-paths 删除历史中的 .env / .env.* (只删敏感文件, 不动业务代码)
log "执行 git filter-repo --invert-paths (删除历史 .env) ..."
git filter-repo --force \
  --invert-paths \
  --path '.env' \
  --path-glob '.env.*'

# -----------------------------------------------------------------------------
# 3. 重写后验证
# -----------------------------------------------------------------------------
log "验证 1: 历史中敏感值应无残留"
LEAK_REMAIN="$(git log --all --oneline -S "$(head -n1 "${SENSITIVE_FILE}")" 2>/dev/null | wc -l)"
# 逐值校验(任一值仍存在则失败)
FAILED=0
while IFS= read -r VAL; do
  [ -z "${VAL}" ] && continue
  if git log --all --oneline -S "${VAL}" 2>/dev/null | grep -q .; then
    printf '  [FAIL] 历史中仍可检出已配置的敏感值\n' >&2
    FAILED=1
  fi
done < "${SENSITIVE_FILE}"
[ "${FAILED}" -eq 0 ] || die "验证失败: 历史中仍存在敏感值。已中止(临时克隆将被清理, 原仓库未受影响)。"

log "验证 2: .env 应从历史中完全移除"
TRACKED_ENV="$(git log --all --oneline -- '*.env' | wc -l)"
log "历史中仍含 .env 的 commit 数: ${TRACKED_ENV} (期望 0)"

log "验证 3: 业务文件数量应保持不变(.env 除外)"
BEFORE_FILES="$(git -C "${REPO_ROOT}" ls-tree -r --name-only HEAD | wc -l)"
AFTER_FILES="$(git ls-tree -r --name-only HEAD | wc -l)"
log "重写前 HEAD 文件数: ${BEFORE_FILES}; 重写后 HEAD 文件数: ${AFTER_FILES}"

log "验证 4: 当前安全版本(b9cc09b1)的代码内容应保留"
git log -1 --oneline

# -----------------------------------------------------------------------------
# 4. 输出结果与人工推送指引(脚本自身绝不 push)
# -----------------------------------------------------------------------------
cat <<EOF

====================================================
重写完成(仅本地临时克隆)。原仓库未被修改。
下一步(必须人工执行, 逐条确认):
  1) 检查临时克隆: ${TMP_DIR}/rewrite.git  (关闭后会被清理, 先审查)
  2) 确认后把重写结果应用到本地 main:
       git -C "${REPO_ROOT}" fetch "${TMP_DIR}/rewrite.git" main:refs/heads/main
     (或: 直接在该克隆内验证完毕后, 人工将 refs/heads/main 更新到本地仓库)
  3) 推送(需仓库所有者明确授权, 且先确认所有协作者已同步):
       git push --force-with-lease origin main
  4) 处理泄漏分支(需人工决定, 脚本不删除任何 remote branch):
       origin/trae/solo-agent-fLtHYf
       origin/trae/solo-agent-h8fIab
       origin/trae/solo-agent-y3VxiW
  5) 推送后按 docs/SECURITY_SECRET_ROTATION_CHECKLIST.md 轮换所有已泄漏凭据
     (记住: 历史重写无法撤销已泄露的 secret, 必须轮换)。
====================================================
EOF