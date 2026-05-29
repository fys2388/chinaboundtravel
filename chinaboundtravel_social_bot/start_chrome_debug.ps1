# Chrome Remote Debug Browser Launcher
# ChinaBound Travel Social Bot
# ================================
#
# HOW TO USE:
# 1. Make sure ALL your Chrome windows are CLOSED first
# 2. Double-click this file OR run in PowerShell:
#    .\start_chrome_debug.ps1
# 3. Wait for Chrome to open with "DevTools listening on port 9222" in the title
# 4. Keep this browser open — DO NOT close it while posting
#
# WHAT THIS DOES:
# - Launches Chrome with remote debugging enabled on port 9222
# - Uses a dedicated profile at C:\chrome_auto_profile
# - Your social accounts are already logged in this profile
# - Python scripts connect to this browser automatically
#
# TO VERIFY IT'S RUNNING:
# Open another tab: http://localhost:9222/json
# You should see JSON with "title" and "webSocketDebuggerUrl"

param(
    [string]$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe",
    [string]$ProfilePath = "C:\chrome_auto_profile",
    [int]$DebugPort = 9222
)

$ErrorActionPreference = "Stop"

# Verify Chrome exists
if (-not (Test-Path $ChromePath)) {
    Write-Host "ERROR: Chrome not found at: $ChromePath" -ForegroundColor Red
    Write-Host "Please install Google Chrome or update the ChromePath variable." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Verify profile exists
if (-not (Test-Path $ProfilePath)) {
    Write-Host "WARNING: Profile folder not found. Creating it now..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $ProfilePath -Force | Out-Null
}

# Kill any existing chrome processes using this profile to avoid port conflicts
$existingProcesses = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*$ProfilePath*" -or $_.CommandLine -like "*--remote-debugging-port=$DebugPort*"
}
if ($existingProcesses) {
    Write-Host "Existing Chrome instances with this profile found. Killing them..." -ForegroundColor Yellow
    $existingProcesses | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Also check if anything is using the debug port
$portCheck = Get-NetTCPConnection -LocalPort $DebugPort -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host "Port $DebugPort is in use. Attempting to free it..." -ForegroundColor Yellow
    $portCheck | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ChinaBound Travel - Chrome Debug Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Chrome Path : $ChromePath" -ForegroundColor Gray
Write-Host "Profile     : $ProfilePath" -ForegroundColor Gray
Write-Host "Debug Port  : $DebugPort" -ForegroundColor Gray
Write-Host ""

# Launch Chrome with remote debugging
$arguments = @(
    "--remote-debugging-port=$DebugPort",
    "--user-data-dir=$ProfilePath",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-popup-blocking",
    "--disable-notifications",
    "--disable-features=ChromeRuntime"
)

$process = Start-Process -FilePath $ChromePath -ArgumentList $arguments -PassThru -WindowStyle Normal

Start-Sleep -Seconds 3

if ($process.HasExited) {
    Write-Host "ERROR: Chrome exited immediately with code $($process.ExitCode)" -ForegroundColor Red
    Write-Host "Try running as Administrator." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Chrome started successfully (PID: $($process.Id))" -ForegroundColor Green
Write-Host ""
Write-Host "NOTE: Keep this Chrome window OPEN while posting." -ForegroundColor Yellow
Write-Host "Close this window when you are done posting." -ForegroundColor Yellow
Write-Host ""
Write-Host "Verifying debug port..."

Start-Sleep -Seconds 2

# Verify the port is listening
$verifyPort = Get-NetTCPConnection -LocalPort $DebugPort -ErrorAction SilentlyContinue
if ($verifyPort) {
    Write-Host "[OK] Port $DebugPort is listening" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run the posting script:" -ForegroundColor Cyan
    Write-Host "  cd e:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot" -ForegroundColor Gray
    Write-Host "  python auto_post_final.py" -ForegroundColor Gray
} else {
    Write-Host "[WARN] Could not verify port $DebugPort. Chrome may still be starting up." -ForegroundColor Yellow
    Write-Host "Wait 5 seconds and check: http://localhost:$DebugPort/json" -ForegroundColor Gray
}

Write-Host ""
