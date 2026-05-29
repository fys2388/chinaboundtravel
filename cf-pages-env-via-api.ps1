# Cloudflare Pages REST API — 环境变量 + Secrets 批量部署脚本
# 支持：普通环境变量（非敏感）和 Secrets（敏感）
# 无需 wrangler，纯 API 调用，可在 CI/CD（GitHub Actions）中运行

# ========== 在这里填入你的凭证 ==========
$env:CLOUDFLARE_ACCOUNT_ID  = "YOUR_CLOUDFLARE_ACCOUNT_ID"   # 来自 Cloudflare Dashboard → Pages → 项目 → Overview 底部
$env:CLOUDFLARE_API_TOKEN  = "YOUR_CLOUDFLARE_API_TOKEN"   # 你的 API Token（需要 Pages Edit 权限）
$PROJECT_NAME               = "chinaboundtravel"
# ==========================================

$BASE_URL = "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/pages/projects/$PROJECT_NAME"

# --------------- Secrets（敏感，通过 /secrets 端点）---------------
$secrets = @{
    "STRIPE_SECRET_KEY"       = "YOUR_STRIPE_SECRET_KEY"
    "STRIPE_WEBHOOK_SECRET"   = "YOUR_STRIPE_WEBHOOK_SECRET"
    "RESEND_API_KEY"          = "YOUR_RESEND_API_KEY"
}

# --------------- 普通环境变量（非敏感，通过 PATCH 直接写）---------------
$env_vars = @{
    "SUCCESS_URL" = "https://chinaboundtravel.com/success/"
    "CANCEL_URL"  = "https://chinaboundtravel.com/pricing/"
}

# =============================================
# 以下无需修改
# =============================================

$headers = @{
    "Authorization" = "Bearer $CLOUDFLARE_API_TOKEN"
    "Content-Type"  = "application/json"
}

# ---------- 1. 先获取项目当前配置（拿到 build_config 等必填字段）----------
Write-Host "Fetching current project config..." -ForegroundColor Cyan
$current = Invoke-RestMethod -Uri $BASE_URL -Method GET -Headers $headers
if (-not $current.success) {
    Write-Host "获取项目配置失败: $($current.errors)" -ForegroundColor Red
    exit 1
}

# ---------- 2. 写入 Secrets ----------
Write-Host "`n=== Deploying Secrets ===" -ForegroundColor Yellow
foreach ($name in $secrets.Keys) {
    $value = $secrets[$name]
    $body  = @{ name = $name; value = $value } | ConvertTo-Json -Compress
    Write-Host "[$name] POSTing..." -NoNewline

    $resp = Invoke-RestMethod `
        -Uri "$BASE_URL/secrets" `
        -Method POST `
        -Headers $headers `
        -Body $body

    if ($resp.success) {
        Write-Host " OK" -ForegroundColor Green
    } else {
        Write-Host " FAILED: $($resp.errors)" -ForegroundColor Red
    }
}

# ---------- 3. 写入普通环境变量（PATCH整个项目，保留原配置）----------
Write-Host "`n=== Deploying Environment Variables ===" -ForegroundColor Yellow

# 构造新的 env_vars 合并到原配置
$newEnvVars = @{}
foreach ($v in $current.result.env_vars.PSObject.Properties) {
    $newEnvVars[$v.Name] = @{ value = $v.Value.value; description = $v.Value.description }
}
foreach ($name in $env_vars.Keys) {
    $newEnvVars[$name] = @{ value = $env_vars[$name]; description = "" }
    Write-Host "[$name] Added" -ForegroundColor Green
}

# 构建完整 PATCH body（必须包含 build_config 等必填字段）
$patchBody = @{
    build_config    = $current.result.build_config
    source          = $current.result.source
    deployment_configs = $current.result.deployment_configs
    env_vars        = $newEnvVars
} | ConvertTo-Json -Depth 10

Write-Host "`nPATCHing project config..." -ForegroundColor Cyan
$patch = Invoke-RestMethod `
    -Uri $BASE_URL `
    -Method PATCH `
    -Headers $headers `
    -Body $patchBody

if ($patch.success) {
    Write-Host "Project updated successfully!" -ForegroundColor Green
    Write-Host "Allow ~60 seconds for CDN cache propagation." -ForegroundColor Cyan
} else {
    Write-Host "PATCH failed: $($patch.errors)" -ForegroundColor Red
}
