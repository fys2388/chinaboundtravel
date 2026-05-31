# Cloudflare Pages Domain Configuration Check Script
$apiToken = "cfat_vZ1BlbSBtrRMcXsOX4aHbkSG1a1cNaUyLMq4vrycecb11fa5"
$accountId = "76b6c886ece7149115e3d334fcec8a02"
$projectName = "chinaboundtravel"

Write-Host "=== Checking Cloudflare Pages Domain Configuration ===" -ForegroundColor Cyan

# Get Project Info
Write-Host "`n1. Getting project info..." -ForegroundColor Yellow
$projectUrl = "https://api.cloudflare.com/client/v4/accounts/$accountId/pages/projects/$projectName"
$headers = @{
    "Authorization" = "Bearer $apiToken"
    "Content-Type" = "application/json"
}

try {
    $projectInfo = Invoke-RestMethod -Uri $projectUrl -Headers $headers -Method Get
    Write-Host "Project Name: $($projectInfo.result.name)" -ForegroundColor Green
    Write-Host "Project ID: $($projectInfo.result.id)" -ForegroundColor Green
    Write-Host "Created On: $($projectInfo.result.created_on)" -ForegroundColor Green
} catch {
    Write-Host "Failed to get project info: $_" -ForegroundColor Red
    exit 1
}

# Get Domain List
Write-Host "`n2. Getting domain list..." -ForegroundColor Yellow
$domainsUrl = "https://api.cloudflare.com/client/v4/accounts/$accountId/pages/projects/$projectName/domains"
try {
    $domains = Invoke-RestMethod -Uri $domainsUrl -Headers $headers -Method Get
    
    if ($domains.result.Count -eq 0) {
        Write-Host "WARNING: No custom domains configured" -ForegroundColor Red
    } else {
        Write-Host "Configured Domains:" -ForegroundColor Green
        foreach ($domain in $domains.result) {
            $status = if ($domain.status -eq "active") { "ACTIVE" } else { "NOT ACTIVE - " + $domain.status }
            Write-Host "  - $($domain.domain): $status" -ForegroundColor Green
            if ($domain.verification_errors) {
                Write-Host "    Verification errors: $($domain.verification_errors -join ', ')" -ForegroundColor Red
            }
        }
    }
} catch {
    Write-Host "Failed to get domain list: $_" -ForegroundColor Red
}

# Check DNS Records
Write-Host "`n3. Checking DNS records..." -ForegroundColor Yellow
$zoneId = "032a874de4e89298d9f492590b08ecba"
$dnsUrl = "https://api.cloudflare.com/client/v4/zones/$zoneId/dns_records"
try {
    $dnsRecords = Invoke-RestMethod -Uri $dnsUrl -Headers $headers -Method Get
    
    Write-Host "Related DNS Records:" -ForegroundColor Green
    foreach ($record in $dnsRecords.result) {
        if ($record.name -match "chinaboundtravel") {
            Write-Host "  - $($record.name) ($($record.type)): $($record.content)" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "Failed to get DNS records: $_" -ForegroundColor Red
}

Write-Host "`n=== Check Complete ===" -ForegroundColor Cyan
