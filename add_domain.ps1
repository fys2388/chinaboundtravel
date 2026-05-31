# Add domain to Cloudflare Pages
$domain = "www.chinaboundtravel.com"
$projectName = "chinaboundtravel"

Write-Host "Attempting to add domain: $domain" -ForegroundColor Cyan

try {
    Write-Host "Adding domain to Pages project..." -ForegroundColor Yellow
    npx wrangler pages domain add $domain --project-name $projectName
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Domain added successfully!" -ForegroundColor Green
    } else {
        Write-Host "Failed to add domain" -ForegroundColor Red
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
