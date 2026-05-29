# ChinaBound Travel - One-click Deploy
Set-Location $PSScriptRoot

Write-Host "Building Hugo site..." -ForegroundColor Cyan
hugo --gc --minify
if ($LASTEXITCODE -ne 0) {
    Write-Host "Hugo build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Deploying to Cloudflare Pages..." -ForegroundColor Cyan
$env:CLOUDFLARE_API_TOKEN = "YOUR_CLOUDFLARE_API_TOKEN"
npx wrangler pages deploy public --project-name chinaboundtravel --branch main

Write-Host "Done!" -ForegroundColor Green
