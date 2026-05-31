# ChinaBound Travel - Windows Task Scheduler Setup
# Run this script as Administrator to configure scheduled tasks

$TaskFolder = "E:\AI\dulizhan\travel-blog"

# Task 1: Daily Inspection (09:30 Beijing Time)
$TaskName1 = "ChinaBound_Daily_Inspection"
$Action1 = New-ScheduledTaskAction -Execute "python" -Argument "boundtravel_daily_inspector.py" -WorkingDirectory $TaskFolder
$Trigger1 = New-ScheduledTaskTrigger -Daily -At "09:30"
$Settings1 = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName $TaskName1 -Action $Action1 -Trigger $Trigger1 -Settings $Settings1 -Force -Description "Daily website inspection for chinaboundtravel.com"
Write-Host "Created: $TaskName1 (Daily 09:30)" -ForegroundColor Green

# Task 2: AI Content Pipeline (Daily 08:00 Beijing Time)
$TaskName2 = "ChinaBound_AI_Pipeline"
$Action2 = New-ScheduledTaskAction -Execute "python" -Argument "agent_pipeline.py" -WorkingDirectory $TaskFolder
$Trigger2 = New-ScheduledTaskTrigger -Daily -At "08:00"
$Settings2 = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName $TaskName2 -Action $Action2 -Trigger $Trigger2 -Settings $Settings2 -Force -Description "AI content generation and publishing pipeline"
Write-Host "Created: $TaskName2 (Daily 08:00)" -ForegroundColor Green

# Task 3: Buffer Social Media Scheduler (Start on boot, run continuously)
$TaskName3 = "ChinaBound_Buffer_Scheduler"
$Action3 = New-ScheduledTaskAction -Execute "python" -Argument "chinaboundtravel_social_bot\buffer_scheduler.py" -WorkingDirectory $TaskFolder
$Trigger3 = New-ScheduledTaskTrigger -AtStartup
$Settings3 = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -RestartInterval (New-TimeSpan -Minutes 5) -RestartCount 3
Register-ScheduledTask -TaskName $TaskName3 -Action $Action3 -Trigger $Trigger3 -Settings $Settings3 -Force -Description "Buffer social media auto-posting scheduler"
Write-Host "Created: $TaskName3 (Startup + Auto-restart)" -ForegroundColor Green

# Task 4: Hugo Build & Deploy (Daily 09:00 Beijing Time)
$TaskName4 = "ChinaBound_Deploy"
$Action4 = New-ScheduledTaskAction -Execute "powershell" -Argument "-File deploy.ps1" -WorkingDirectory $TaskFolder
$Trigger4 = New-ScheduledTaskTrigger -Daily -At "09:00"
$Settings4 = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName $TaskName4 -Action $Action4 -Trigger $Trigger4 -Settings $Settings4 -Force -Description "Build Hugo site and deploy to Cloudflare Pages"
Write-Host "Created: $TaskName4 (Daily 09:00)" -ForegroundColor Green

Write-Host "`n=== All Scheduled Tasks Created ===" -ForegroundColor Cyan
Write-Host "View in: Task Scheduler -> Task Scheduler Library" -ForegroundColor Yellow

# List all created tasks
Get-ScheduledTask | Where-Object { $_.TaskName -like "ChinaBound*" } | Format-Table TaskName, State, LastRunTime -AutoSize
