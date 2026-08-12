# ??? .env ????????????? secret?
if (Test-Path .env) {?
  $envMap = @{}?
  Get-Content .env | ForEach-Object {?
    if ($_ -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $envMap[$matches[1]] = $matches[2] }?
  }?
  if (-not $env:DEEPSEEK_API_KEY) { $env:DEEPSEEK_API_KEY = $envMap["DEEPSEEK_API_KEY"] }?
  if (-not $env:DEEPSEEK_BACKUP_API_KEY) { $env:DEEPSEEK_BACKUP_API_KEY = $envMap["DEEPSEEK_API_KEY"] }?
  if (-not $env:FEISHU_WEBHOOK_URL) { $env:FEISHU_WEBHOOK_URL = $envMap["FEISHU_WEBHOOK_URL"] }?
  if (-not $env:GEMINI_API_KEY) { $env:GEMINI_API_KEY = $envMap["GEMINI_API_KEY"] }?
}?
if (-not $env:DEEPSEEK_API_KEY) { Write-Warning "DEEPSEEK_API_KEY ???????????? .env ???" }?
if (-not $env:FEISHU_WEBHOOK_URL) { Write-Warning "FEISHU_WEBHOOK_URL ???????????? .env ???" }?

Write-Host "=== 开始全链路测试 ==="
Write-Host "1. 生成文章..."

cd e:\AI\dulizhan\travel-blog
python chinaboundtravel_social_bot/joran_blog_generator.py