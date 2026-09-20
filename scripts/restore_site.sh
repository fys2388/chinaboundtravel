#!/usr/bin/env bash
# 站点回滚工具（配套 .github/workflows/site-backup-daily.yml）
#
# 用法：
#   ./scripts/restore_site.sh --list              列出可用回滚点（默认）
#   ./scripts/restore_site.sh <tag|sha>           打印针对该点的回滚方案（只读，不执行）
#   ./scripts/restore_site.sh --branch <tag|sha>  在本地创建 rollback/<sha> 分支并 checkout
#
# 安全边界（本脚本刻意不做的事）：
#   * 不 push、不 force-push、不 reset、不删 tag、不碰 main
#   * --branch 只创建**本地**分支，是否推送/如何合入由人决定
#   * 仓库纪律是 rebase-only，优先用 git revert 而非 reset 回滚
set -euo pipefail

cd "$(dirname "$0")/.."
BRANCH="backup/site-snapshot"

die() { echo "!! $*" >&2; exit 2; }

fetch_tags() {
  git fetch --tags --quiet origin 2>/dev/null || true
}

list_points() {
  fetch_tags
  local tags
  tags="$(git tag -l 'backup/site-*' --sort=-creatordate 2>/dev/null || true)"
  if [ -z "$tags" ]; then
    echo "（尚无 backup/site-* 标签。若从未运行过 site-backup-daily 工作流，属正常。）"
    return 0
  fi
  local n=0
  echo "可用回滚点（最新在前，最多 30 个）："
  echo "  TAG                          COMMIT DATE           SHA"
  echo "$tags" | head -30 | while read -r t; do
    [ -z "$t" ] && continue
    printf '  %-30s %-20s %s\n' \
      "$t" \
      "$(git log -1 --format=%ci "$t" 2>/dev/null | cut -d' ' -f1)" \
      "$(git rev-parse --short "$t")"
  done
  echo
  echo "镜像分支 ${BRANCH}:"
  if git rev-parse --verify --quiet "${BRANCH}^{commit}" >/dev/null; then
    printf '  %-30s %-20s %s\n' "${BRANCH}" \
      "$(git log -1 --format=%ci "${BRANCH}" | cut -d' ' -f1)" \
      "$(git rev-parse --short "${BRANCH}")"
  else
    echo "  （本地不存在，需先 git fetch origin ${BRANCH}）"
  fi
}

resolve() {
  local target="$1"
  if ! git rev-parse --verify --quiet "${target}^{commit}" >/dev/null; then
    fetch_tags
    if ! git rev-parse --verify --quiet "${target}^{commit}" >/dev/null; then
      die "无法解析目标: ${target}（用 --list 查看可用回滚点）"
    fi
  fi
}

plan() {
  local target="$1"
  resolve "$target"
  local sha short
  sha="$(git rev-parse "$target")"
  short="$(git rev-parse --short "$target")"
  local main_short
  main_short="$(git rev-parse --short origin/main 2>/dev/null || git rev-parse --short main)"

  echo
  echo "回滚目标: ${target}"
  echo "  sha    : ${sha}"
  echo "  提交   : $(git log -1 --format='%ci  %an  %s' "$target")"
  echo "  origin/main: ${main_short}"
  echo
  local behind
  behind="$(git rev-list --count "${target}..origin/main" 2>/dev/null || echo '?')"
  echo "  目标落后 origin/main: ${behind} 个提交"
  echo
  if [ "$behind" = "0" ]; then
    echo "该点就是当前 main，无需回滚。"
    return 0
  fi
  echo "=== 方式 A — revert 最近提交（推荐，保留完整历史）==="
  echo
  echo "  git fetch origin"
  echo "  git checkout -B rollback/${short} origin/main"
  echo "  git revert --no-commit origin/main~${behind}..origin/main   # 或按提交范围手工选择"
  echo "  git commit -m 'revert: rollback to ${target}'"
  echo "  git push origin rollback/${short}"
  echo "  # 开 PR，人工复核后合入 main。不要直接推 main。"
  echo
  echo "=== 方式 B — 切到该快照（破坏性，仅紧急情况）==="
  echo
  echo "  git checkout -B rollback/${short} \"${target}\""
  echo "  git push origin rollback/${short}"
  echo "  # 之后仍需人工复核，用 PR 合入。此分支丢弃了中间 ${behind} 个提交。"
  echo
  echo "=== 方式 C — 只恢复单个文件 ==="
  echo
  echo "  git checkout \"${target}\" -- <path/to/file>"
  echo
  echo "⚠️  本脚本未执行任何写操作。以上指令需人工复核后自行运行。"
}

make_branch() {
  local target="$1"
  resolve "$target"
  local short
  short="$(git rev-parse --short "$target")"
  local branch="rollback/${short}"
  if git rev-parse --verify --quiet "${branch}^{commit}" >/dev/null; then
    die "本地已存在分支 ${branch}（未删除，也未覆盖）"
  fi
  git branch "$branch" "$target"
  echo "已创建本地分支 ${branch} -> $(git rev-parse "$target")"
  echo "注意：只创建了本地分支，未推送。checkout 请用：git switch ${branch}"
}

case "${1:-}" in
  ""|--list|list)          list_points ;;
  --branch)                [ "${2:-}" ] || die "--branch 需要 <tag|sha> 参数"
                           make_branch "$2" ;;
  --help|-h)               sed -n '2,12p' "$0" ;;
  *)                       plan "$1" ;;
esac
