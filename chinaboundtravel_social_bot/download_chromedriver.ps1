# Auto-download matching chromedriver for Chrome 148.0.7778.179
$chromeVersion = "148.0.7778.179"
$majorVersion = "148"
$downloadUrl = "https://storage.googleapis.com/chrome-for-testing-public/$chromeVersion/win64/chromedriver-win64.zip"
$zipPath = "E:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot\chromedriver.zip"
$extractPath = "E:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot\chromedriver-temp"
$targetPath = "E:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot\chromedriver.exe"

Write-Host "Downloading chromedriver $chromeVersion..."

# Download
Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing

Write-Host "Extracting..."
Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

# Move chromedriver.exe to target
$driverSource = "$extractPath\chromedriver-win64\chromedriver.exe"
if (Test-Path $driverSource) {
    Copy-Item -Path $driverSource -Destination $targetPath -Force
    Write-Host "[OK] chromedriver.exe installed to: $targetPath"
} else {
    Write-Host "[ERROR] chromedriver.exe not found in extracted archive"
    exit 1
}

# Cleanup
Remove-Item -Path $zipPath -Force
Remove-Item -Path $extractPath -Recurse -Force

# Verify
$driverVersion = & $targetPath --version 2>$null
Write-Host "Installed: $driverVersion"

Write-Host ""
Write-Host "Chromedriver ready! Now run: python auto_post_final.py"
