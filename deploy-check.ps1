# 部署前检查脚本
Write-Host "检查 wrangler 登录状态..." -ForegroundColor Cyan
npx wrangler whoami 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "未登录，正在打开浏览器登录..." -ForegroundColor Yellow
    npx wrangler login
} else {
    Write-Host "已登录，开始部署..." -ForegroundColor Green
    hugo --gc --minify
    npx wrangler pages deploy public --project-name chinaboundtravel --branch main
}
