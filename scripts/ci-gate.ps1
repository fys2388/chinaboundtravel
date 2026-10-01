#!/usr/bin/env pwsh
#
# CI Gate — chinaboundtravel.com quality gate
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/ci-gate.ps1            # build + scan
#   powershell -ExecutionPolicy Bypass -File scripts/ci-gate.ps1 --no-build # scan only
#
# Dependencies:
#   - Hugo v0.147+ (for build)
#   - Python 3.8+ (for scanner)
#   - PowerShell 5.1+ (for this script)
#
# CI integration:
#   GitHub Actions:
#     - name: Hugo Build
#       run: hugo build --minify --cleanDestinationDir
#     - name: CI Gate
#       run: powershell -ExecutionPolicy Bypass -File scripts/ci-gate.ps1 --no-build
#
#   Cloudflare Pages:
#     - Add as post-build step in wrangler.toml or build script
#
# Exit codes:
#   0 = all checks passed (green)
#   1 = one or more checks failed (red)
#

param(
    [switch]$NoBuild
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$Scanner = Join-Path $ScriptDir 'ci_gate_scanner.py'
$ReportFile = Join-Path $RepoRoot 'reports\ci_gate_report.json'

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CI Gate - chinaboundtravel.com" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python availability
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python not found. Install Python 3.8+." -ForegroundColor Red
    exit 1
}
$PythonPath = $pythonCmd.Source
Write-Host "[info] Using Python: $PythonPath"

# Build step
if (-not $NoBuild) {
    Write-Host ""
    Write-Host "[build] Running Hugo build..." -ForegroundColor Yellow
    $env:WEB3FORMS_ACCESS_KEY = "test"  # placeholder to pass build
    $buildResult = & hugo build --minify --cleanDestinationDir 2>&1
    $buildExit = $LASTEXITCODE
    if ($buildExit -ne 0) {
        Write-Host "[build] FAILED (exit $buildExit)" -ForegroundColor Red
        $buildResult | Select-Object -Last 10
        Write-Host ""
        Write-Host "Build failed — aborting scan." -ForegroundColor Red
        # Write a failure report
        $failReport = @{
            timestamp = (Get-Date).ToUniversalTime().ToString("o")
            build = @{ passed = $false; error = "hugo build exited with code $buildExit" }
            checks = @()
            summary = @{ total = 8; passed = 0; failed = 0; build_failed = $true }
        }
        $json = $failReport | ConvertTo-Json -Depth 5
        $reportDir = Join-Path $RepoRoot 'reports'
        if (-not (Test-Path $reportDir)) { New-Item -ItemType Directory -Path $reportDir -Force | Out-Null }
        Set-Content -Path $ReportFile -Value $json -Encoding UTF8
        Write-Host "[report] Failure report written to reports\ci_gate_report.json"
        exit 1
    }
    Write-Host "[build] PASSED" -ForegroundColor Green
} else {
    Write-Host "[info] Skipping build (--no-build)" -ForegroundColor Cyan
}

# Scan step (always pass --no-build to scanner since PS handles build)
Write-Host ""
Write-Host "[scan] Running CI gate checks..." -ForegroundColor Yellow
& $PythonPath $Scanner --no-build
$scanExit = $LASTEXITCODE

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($scanExit -eq 0) {
    Write-Host "  CI Gate: ALL PASSED (green)" -ForegroundColor Green
} else {
    Write-Host "  CI Gate: SOME CHECKS FAILED (red)" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[report] See $ReportFile for full details"

exit $scanExit
