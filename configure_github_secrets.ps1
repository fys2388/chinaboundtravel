# GitHub Secrets Configuration Script
# Run this script after authenticating with: gh auth login

$Repo = "fys2388/chinaboundtravel"

Write-Host "=== Configuring GitHub Secrets for $Repo ===" -ForegroundColor Cyan

# Secrets to configure
$Secrets = @{
    "CLOUDFLARE_API_TOKEN" = "YOUR_CLOUDFLARE_API_TOKEN"
    "CLOUDFLARE_ACCOUNT_ID" = "YOUR_CLOUDFLARE_ACCOUNT_ID"
    "STRIPE_SECRET_KEY" = "YOUR_STRIPE_SECRET_KEY"
    "FEISHU_WEBHOOK_URL" = "YOUR_FEISHU_WEBHOOK_URL"
}

foreach ($SecretName in $Secrets.Keys) {
    $SecretValue = $Secrets[$SecretName]
    Write-Host "Setting $SecretName..." -ForegroundColor Yellow
    
    # Use gh cli to set secret
    $SecretValue | gh secret set $SecretName --repo $Repo
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: $SecretName" -ForegroundColor Green
    } else {
        Write-Host "  FAILED: $SecretName" -ForegroundColor Red
    }
}

Write-Host "`n=== Secrets Configuration Complete ===" -ForegroundColor Cyan
Write-Host "View secrets at: https://github.com/$Repo/settings/secrets/actions" -ForegroundColor Yellow
