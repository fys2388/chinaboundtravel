# Quick Deploy Script for Vercel

Write-Host "Starting Vercel deployment..." -ForegroundColor Cyan

# Start deployment in new window
Start-Process powershell -ArgumentList "-Command", "cd 'e:\AI\dulizhan\travel-blog'; Write-Host 'Starting deployment...'; npx vercel deploy --prod" -Wait -NoNewWindow

Write-Host "Deployment completed!" -ForegroundColor Green