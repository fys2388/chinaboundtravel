@echo off
chcp 65001 >nul
title ChinaBound Travel — 一键社媒发帖

:: ============================================================
:: 一键发帖脚本 — 复用你已有的 Chrome 登录状态
:: ============================================================

echo ==========================================
echo  ChinaBound Travel — 一键社媒发帖
echo ==========================================
echo.

:: 检查 Python
echo [1/5] 检查 Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python！
    echo 请安装 Python 3.10 或 3.12
    pause
    exit /b 1
)
python --version
echo.

:: 检查 selenium
echo [2/5] 检查 selenium...
python -c "import selenium" >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] selenium 未安装，正在自动安装...
    python -m pip install selenium -q
    if %errorlevel% neq 0 (
        echo [错误] selenium 安装失败，请手动运行：
        echo    python -m pip install selenium
        pause
        exit /b 1
    )
    echo [OK] selenium 安装完成
) else (
    echo [OK] selenium 已安装
)
echo.

:: 关闭所有 Chrome（避免 profile 冲突）
echo [3/5] 关闭现有 Chrome 进程...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 >nul
echo [OK] Chrome 已关闭
echo.

:: 启动 Chrome 调试模式（复用你的登录状态）
echo [4/5] 启动 Chrome 调试模式...
echo 正在使用你的 Chrome 登录数据启动调试浏览器...
set CHROME_EXE="C:\Program Files\Google\Chrome\Application\chrome.exe"
set USER_PROFILE=%LOCALAPPDATA%\Google\Chrome\User Data

%CHROME_EXE% --remote-debugging-port=9222 --user-data-dir="%USER_PROFILE%" --no-first-run >nul 2>&1 &

:: 等待 Chrome 启动
timeout /t 3 >nul

:: 检查端口
echo 检查调试端口...
timeout /t 2 >nul

echo.
echo ==========================================
echo  [5/5] 准备就绪！
echo ==========================================
echo.
echo  Chrome 调试浏览器已启动（使用你的登录状态）
echo  如果你的账号还在登录状态，可以直接开始发帖
echo.
echo  如果账号未登录，请先在弹出的 Chrome 中登录：
echo    • Reddit    reddit.com
echo    • Pinterest  pinterest.com
echo    • Quora     quora.com
echo    • Medium    medium.com
echo    • Facebook  facebook.com
echo.
echo  按任意键开始发帖...
echo ==========================================
pause >nul

:: 运行发帖脚本
echo.
echo [开始发帖] 正在运行 auto_post_final.py...
echo ==========================================
echo.
cd /d "E:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot"
python auto_post_final.py

echo.
echo ==========================================
echo  发帖完成！
echo ==========================================
echo.
echo 按任意键关闭窗口...
pause >nul
