#!/usr/bin/env pwsh
# GitHub Secrets 批量添加工具
# 用法：.\Add-GitHubSecrets.ps1 -EnvFile ".env"

param(
    [string]$EnvFile = ".env",
    [string]$RepoOwner = "fys2388",
    [string]$RepoName = "chinaboundtravel"
)

# 颜色输出函数
function Write-Color($text, $color) {
    Write-Host $text -ForegroundColor $color
}

# 检查 gh CLI 是否安装
function Test-GhCli {
    try {
        $null = gh --version
        return $true
    } catch {
        return $false
    }
}

# 检查 GitHub 登录状态
function Test-GhAuth {
    try {
        $result = gh auth status 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

# 添加单个 Secret
function Add-GitHubSecret {
    param(
        [string]$Name,
        [string]$Value
    )
    
    if ($Value -eq "" -or $Value -eq $null) {
        Write-Color "  ⚠️  $Name : 值为空，跳过" Yellow
        return
    }
    
    Write-Host "  → 添加 $Name ..." -NoNewline
    
    # 使用 gh secret set 命令
    $result = gh secret set $Name --body $Value --repo "$RepoOwner/$RepoName" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Color " ✅ 成功" Green
    } else {
        Write-Color " ❌ 失败" Red
        Write-Host "     错误：$result"
    }
}

# 主函数
function Main {
    Write-Color "`n========================================" Blue
    Write-Color " GitHub Secrets 批量添加工具" Blue
    Write-Color "========================================`n" Blue
    
    # 检查 gh CLI
    if (-not (Test-GhCli)) {
        Write-Color "错误：未找到 gh CLI，请先安装 GitHub CLI" Red
        Write-Host "安装方法：https://cli.github.com/"
        exit 1
    }
    
    # 检查登录状态
    if (-not (Test-GhAuth)) {
        Write-Color "错误：未登录 GitHub，请先运行 gh auth login" Red
        exit 1
    }
    
    # 检查 .env 文件
    if (-not (Test-Path $EnvFile)) {
        Write-Color "错误：未找到 .env 文件：$EnvFile" Red
        exit 1
    }
    
    Write-Color "✓ GitHub CLI 已安装并登录" Green
    Write-Color "✓ 仓库：$RepoOwner/$RepoName" Green
    Write-Color "✓ 配置文件：$EnvFile`n" Green
    
    # 读取 .env 文件
    Write-Color "开始读取 .env 文件..." Yellow
    $envContent = Get-Content $EnvFile -Raw
    $envVars = [regex]::Matches($envContent, '^(\w+)=(.*)', 'Multiline')
    
    $total = $envVars.Count
    $added = 0
    $skipped = 0
    
    Write-Color "`n开始批量添加 Secrets：`n" Blue
    
    foreach ($match in $envVars) {
        $name = $match.Groups[1].Value
        $value = $match.Groups[2].Value.Trim()
        
        # 跳过空值
        if ($value -eq "" -or $value -eq $null) {
            Write-Color "  ⚠️  $name : 值为空，跳过" Yellow
            $skipped++
            continue
        }
        
        # 添加 Secret
        $result = gh secret set $name --body $value --repo "$RepoOwner/$RepoName" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Color "  ✅ $name" Green
            $added++
        } else {
            Write-Color "  ❌ $name : 失败" Red
        }
    }
    
    # 输出总结
    Write-Color "`n========================================" Blue
    Write-Color " 添加完成！" Blue
    Write-Color "========================================" Blue
    Write-Color "总计：$total 个变量" White
    Write-Color "成功添加：$added 个" Green
    Write-Color "跳过（空值）：$skipped 个" Yellow
    Write-Color "`n请访问以下链接查看配置的 Secrets：" Blue
    Write-Color "https://github.com/$RepoOwner/$RepoName/settings/secrets/actions" Blue
    Write-Color "`n" Blue
}

# 执行主函数
Main
