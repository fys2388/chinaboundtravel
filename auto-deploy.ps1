# Auto Deployment Script for Hugo Site to Vercel

$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host "   ChinaBound Travel Blog Auto Deployment"
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

# Create vercel.json if not exists
if (-not (Test-Path "vercel.json")) {
    Write-Host "Creating vercel.json..." -ForegroundColor Cyan
    $vercelConfig = @{
        builds = @(
            @{
                src = "package.json"
                use = "@vercel/static-build"
                config = @{
                    distDir = "public"
                    command = "hugo --gc --minify"
                }
            }
        )
        routes = @(
            @{
                src = "/(.*)"
                dest = "/$1"
            }
        )
        git = @{
            submodules = $true
        }
    } | ConvertTo-Json -Depth 3
    Set-Content -Path "vercel.json" -Value $vercelConfig
    Write-Host "✅ vercel.json created" -ForegroundColor Green
}

# Deploy using vercel deploy
Write-Host "`nDeploying to Vercel..." -ForegroundColor Cyan
try {
    # Use echo to pipe Y to confirm linking
    $proc = Start-Process -FilePath "npx" -ArgumentList "vercel","deploy","--prod" -Wait -PassThru -NoNewWindow -RedirectStandardInput "input.txt" -RedirectStandardOutput "output.txt" -RedirectStandardError "error.txt"
    
    # Write Y to input file for confirmation
    "Y" | Out-File -FilePath "input.txt" -Encoding ASCII
    
    if ($proc.ExitCode -ne 0) {
        $errorContent = Get-Content "error.txt" -Raw
        throw "Vercel deployment failed with exit code $($proc.ExitCode): $errorContent"
    }
    
    $outputContent = Get-Content "output.txt" -Raw
    Write-Host "✅ Deployment completed successfully" -ForegroundColor Green
    Write-Host "Output: $outputContent"
} catch {
    Write-Host "ERROR: Vercel deployment failed - $_" -ForegroundColor Red
    exit 1
} finally {
    # Cleanup temp files
    Remove-Item "input.txt" -ErrorAction SilentlyContinue
    Remove-Item "output.txt" -ErrorAction SilentlyContinue
    Remove-Item "error.txt" -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "=========================================="
Write-Host "   Deployment Complete!" -ForegroundColor Green
Write-Host "=========================================="