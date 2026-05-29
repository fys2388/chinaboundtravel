@echo off
cls
title ChinaBound Travel Social Poster

echo =====================================
echo  ChinaBound Travel - Social Poster
echo =====================================
echo.

echo [1/3] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.10 or 3.12
    pause
    exit /b 1
)
echo.

echo [2/3] Checking selenium...
python -c "import selenium" 2>nul
if errorlevel 1 (
    echo Installing selenium...
    python -m pip install selenium -q
    if errorlevel 1 (
        echo ERROR: Failed to install selenium
        echo Run: python -m pip install selenium
        pause
        exit /b 1
    )
    echo OK: selenium installed
) else (
    echo OK: selenium is ready
)
echo.

echo [3/3] Starting Chrome debug mode...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 >nul

echo Starting Chrome with remote debugging on port 9222...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data" --no-first-run --no-default-browser-check
timeout /t 3 >nul
echo.

echo =====================================
echo  Chrome started in debug mode
echo  Port: 9222
echo =====================================
echo.
echo If accounts are logged in, press any key to start posting
echo If not, log in first then press any key
echo.
pause
echo.

cd /d "E:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot"
echo Running auto_post_final.py...
echo.
python auto_post_final.py

echo.
echo =====================================
echo  Done!
echo =====================================
pause
