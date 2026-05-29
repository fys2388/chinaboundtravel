@echo off
chcp 65001 >nul
echo ========================================
echo   ChinaBound Travel - 一键发布脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Hugo 构建中...
call hugo --environment production --gc --minify
if errorlevel 1 (
    echo.
    echo [ERROR] Hugo 构建失败！
    pause
    exit /b 1
)
echo [OK] 构建完成
echo.

echo [2/2] Cloudflare Pages 部署中...
call npx wrangler pages deploy public --project-name chinaboundtravel --branch main
if errorlevel 1 (
    echo.
    echo [ERROR] 部署失败！
    pause
    exit /b 1
)

echo.
echo ========================================
echo   部署完成！线上已更新
echo ========================================
pause
