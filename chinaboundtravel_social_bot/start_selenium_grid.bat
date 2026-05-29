@echo off
:: ============================================================
:: ChinaBound Travel — Selenium Grid 一键启动脚本
:: 使用方法：双击运行即可
:: ============================================================

echo ==========================================
echo  ChinaBound Travel — Selenium Grid
echo ==========================================
echo.

:: 检查 Java
java -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Java，请先安装：
    echo    https://www.oracle.com/java/technologies/downloads/
    echo    或：choco install openjdk11
    pause
    exit /b 1
)

:: 清理旧进程
echo [1/4] 清理旧进程...
taskkill /F /IM chromedriver.exe >nul 2>&1
taskkill /F /IM chrome.exe >nul 2>&1
taskkill /F /IM java.exe >nul 2>&1
timeout /t 2 >nul

:: 下载 Selenium Server（如果不存在）
set SELENIUM_JAR=selenium-server-4.24.0.jar
set SELENIUM_URL=https://github.com/SeleniumHQ/selenium/releases/download/selenium-4.24.0/selenium-server-4.24.0.jar

if not exist "%~dp0%SELENIUM_JAR%" (
    echo [2/4] 下载 Selenium Server 4.24.0（首次需要几MB）...
    powershell -Command "Invoke-WebRequest -Uri '%SELENIUM_URL%' -OutFile '%~dp0%SELENIUM_JAR%'"
) else (
    echo [2/4] Selenium Server 已存在，跳过下载
)

:: 启动 Selenium Grid Hub
echo [3/4] 启动 Selenium Grid Hub（端口 4444）...
start "SeleniumGrid" java -jar "%~dp0%SELENIUM_JAR%" hub --port 4444
timeout /t 3 >nul

:: 启动 Chrome Node（使用已有 Chrome 安装 + 调试端口）
echo [4/4] 启动 Chrome Debug Node...
start "ChromeNode" java -jar "%~dp0%SELENIUM_JAR%" node --port 5555 ^
    --detect-drivers false ^
    --selenium-manager false ^
    --browser "chrome,port=9222,bin=C:\Program Files\Google\Chrome\Application\chrome.exe"

echo.
echo ==========================================
echo  Selenium Grid 启动完成！
echo.
echo  Hub 控制台：http://localhost:4444
echo  本机IP查询：ipconfig
echo.
echo  把本机IP告诉我，配置到 auto_post_final.py
echo ==========================================
echo.
echo 按任意键退出...
pause >nul
