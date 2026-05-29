# Static Deployment Script for Hugo Site
# This script builds the Hugo site and deploys to Vercel

$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host "   ChinaBound Travel Blog Deployment"
Write-Host "=========================================="
Write-Host ""

# Build Hugo site
Write-Host "Building Hugo site..." -ForegroundColor Cyan
try {
    & "C:\Users\神魂之人\bin\hugo.exe" --gc --minify
    if ($LASTEXITCODE -ne 0) {
        throw "Hugo build failed with exit code $LASTEXITCODE"
    }
    Write-Host "✅ Hugo build completed successfully" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Hugo build failed - $_" -ForegroundColor Red
    exit 1
}

# Deploy to Vercel
Write-Host "`nDeploying to Vercel..." -ForegroundColor Cyan
try {
    & npx vercel --prod --confirm
    if ($LASTEXITCODE -ne 0) {
        throw "Vercel deployment failed with exit code $LASTEXITCODE"
    }
    Write-Host "✅ Deployment completed successfully" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Vercel deployment failed - $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=========================================="
Write-Host "   Deployment Complete!" -ForegroundColor Green
Write-Host "=========================================="