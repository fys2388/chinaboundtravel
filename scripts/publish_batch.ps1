# 定时草稿发布脚本（一次性批次）
# 用法：powershell -File scripts/publish_batch.ps1 -Batch 1
# 每批：移动 _draft → posts、改 front-matter、Hugo 构建验证、git 提交推送、GSC 提交。
# 全程幂等：目标文件已存在则跳过该篇（前次已生效）。

param(
  [int]$Batch = 1
)

$ErrorActionPreference = "Stop"
$Repo = "E:\AI\dulizhan\travel-blog"
Set-Location $Repo

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

if ($Batch -eq 1) {
  $items = @(
    @{ Src = "content/_draft/2026-08-23-kung-fu-and-martial-arts-in-china-where-to-see-and-train-guide-attempt3.md";
       Slug = "kung-fu-and-martial-arts-in-china";
       Title = "Kung Fu & Martial Arts in China" }
  )
} elseif ($Batch -eq 2) {
  $items = @(
    @{ Src = "content/_draft/2026-08-23-china-solo-travel-guide-safety-hostels-and-making-friends-attempt2.md";
       Slug = "china-solo-travel-guide-safety-hostels-and-making-friends";
       Title = "China Solo Travel Guide" },
    @{ Src = "content/_draft/2026-08-26-china-travel-etiquette-tipping-photos-and-unwritten-rules-guide-attempt1.md";
       Slug = "china-travel-etiquette-tipping-photos-and-unwritten-rules-guide";
       Title = "China Travel Etiquette Guide" }
  )
} else {
  Write-Error "未知批次: $Batch（支持 1 或 2）"
}

foreach ($it in $items) {
  $src = $it.Src
  $dst = "content/posts/$($it.Slug).md"

  Write-Step "处理: $($it.Title)"

  if (Test-Path $dst) {
    Write-Host "   跳过（目标已存在，前次已生效）: $dst" -ForegroundColor Yellow
    continue
  }
  if (-not (Test-Path $src)) {
    Write-Host "   跳过（源文件不存在）: $src" -ForegroundColor Yellow
    continue
  }

  Move-Item $src $dst

  $txt = Get-Content $dst -Raw -Encoding UTF8
  # front-matter: draft: "true" / draft: true → draft: false
  $txt = [regex]::Replace($txt, '^(?m)draft:\s*"?true"?\s*$', 'draft: false')
  # audit_status: "pending" / pending → "pass2"
  $txt = [regex]::Replace($txt, '^(?m)audit_status:\s*"?pending"?\s*$', 'audit_status: "pass2"')
  Set-Content $dst $txt -Encoding UTF8 -NoNewline
  Write-Host "   已移动 + front-matter 更新: $dst"
}

Write-Step "Hugo 构建验证"
hugo build 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Error "Hugo 构建失败（exit $LASTEXITCODE），中止本批（人工介入）"
}
Write-Host "   Hugo 构建通过" -ForegroundColor Green

Write-Step "git 提交推送"
$env:PYTHONIOENCODING = "utf-8"
git add -A
if (-not (git diff --staged --quiet)) {
  $batchLabel = if ($Batch -eq 1) { "kung-fu-martial-arts" } else { "china-solo-travel + china-travel-etiquette" }
  git commit -m "feat(content): publish $batchLabel batch $Batch"
  git pull --rebase origin main
  git push origin main
  Write-Host "   已推送（Cloudflare Pages 自动部署）" -ForegroundColor Green
} else {
  Write-Host "   无变更可提交（本批全部跳过）" -ForegroundColor Yellow
}

Write-Step "GSC 提交新页"
python scripts/gsc_index_submit.py --optimized 2>&1 | Select-Object -First 15

Write-Step "批次 $Batch 完成"
