# Cloudflare Pages Secrets 批量部署脚本
# 用法：填入下面的值，然后在 PowerShell 中运行： .\setup-secrets.ps1
# 注意：此脚本必须在你本地机器运行（你的 API Token 有 IP 白名单限制）

$PROJECT_NAME = "chinaboundtravel"

# ========== 在这里填入你的真实密钥 ==========
$secrets = @{
    "STRIPE_SECRET_KEY"       = "***REMOVED***"
    "STRIPE_WEBHOOK_SECRET"   = "***REMOVED***"
    "RESEND_API_KEY"          = "***REMOVED***"
    "SUCCESS_URL"             = "https://chinaboundtravel.com/success/"
    "CANCEL_URL"              = "https://chinaboundtravel.com/pricing/"
}
# =============================================

foreach ($name in $secrets.Keys) {
    $value = $secrets[$name]
    Write-Host "`n[$name] Deploying..." -ForegroundColor Cyan

    # 通过管道非交互式写入 secret
    $value | npx wrangler pages secret put $name --project-name $PROJECT_NAME 2>$null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[$name] OK" -ForegroundColor Green
    } else {
        Write-Host "[$name] FAILED (检查 wrangler 是否已登录: npx wrangler login)" -ForegroundColor Red
    }
}

Write-Host "`nDone. 约 60 秒后自动生效。" -ForegroundColor Green
