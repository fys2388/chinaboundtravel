@echo off
chcp 65001 >nul
echo ================================================
echo    视频流水线启动脚本
echo ================================================
echo.

set PYTHON_PATH=C:\Users\神魂之人\AppData\Roaming\Accio\pre-install\python\python.exe
set SCRIPT_DIR=%~dp0
set OUTPUT_DIR=%SCRIPT_DIR%output

if not exist "%PYTHON_PATH%" (
    echo 错误: Python未找到!
    echo 请检查PYTHON_PATH是否正确配置
    pause
    exit /b 1
)

:MENU
cls
echo ================================================
echo    视频流水线 - 主菜单
echo ================================================
echo.
echo 请选择操作:
echo.
echo   1. 运行视频生成流水线
echo   2. 启动浏览器上传界面 (推荐)
echo   3. 自动上传到社媒平台 (Selenium)
echo   4. 退出
echo.
set /p "choice=输入选项 [1-4]: "

if "%choice%"=="1" goto RUN_PIPELINE
if "%choice%"=="2" goto START_WEB
if "%choice%"=="3" goto AUTO_UPLOAD
if "%choice%"=="4" goto EXIT

echo.
echo 无效选项，请重新输入!
pause
goto MENU

:RUN_PIPELINE
cls
echo ================================================
echo    正在运行视频生成流水线...
echo ================================================
echo.
"%PYTHON_PATH%" "%SCRIPT_DIR%main.py"
echo.
echo ================================================
echo    流水线执行完成
echo ================================================
echo.
echo 视频文件保存在: %OUTPUT_DIR%
echo.
echo 如需上传到社交媒体，请选择选项2启动浏览器界面
echo.
pause
goto MENU

:START_WEB
cls
echo ================================================
echo    启动浏览器上传界面
echo ================================================
echo.
echo 服务器启动中...
echo.
echo 访问地址: http://localhost:8080
echo.
echo 按 Ctrl+C 停止服务器
echo ================================================
"%PYTHON_PATH%" "%SCRIPT_DIR%web_uploader.py"
pause
goto MENU

:AUTO_UPLOAD
cls
echo ================================================
echo    自动上传到社媒平台
echo ================================================
echo.
echo 本功能使用Selenium自动操作浏览器上传视频
echo.
echo 请选择目标平台:
echo   1. Buffer
echo   2. TikTok
echo   3. YouTube
echo   4. 全部平台
echo.
set /p "platform_choice=输入平台选项 [1-4]: "

set "platforms=buffer"
if "%platform_choice%"=="1" set "platforms=buffer"
if "%platform_choice%"=="2" set "platforms=tiktok"
if "%platform_choice%"=="3" set "platforms=youtube"
if "%platform_choice%"=="4" set "platforms=buffer,tiktok,youtube"

echo.
echo 正在搜索视频文件...
echo.

for /f "delims=" %%f in ('dir /b /o-d "%OUTPUT_DIR%\*.mp4" 2^>nul') do (
    set "latest_video=%%f"
    goto :found_video
)
:found_video

if not defined latest_video (
    echo 未找到视频文件!
    echo 请先运行选项1生成视频
    pause
    goto MENU
)

set "video_path=%OUTPUT_DIR%\%latest_video%"
echo 找到最新视频: %video_path%
echo.
echo 正在启动自动上传...
echo.
echo 注意: 首次使用需要手动完成Google账户登录
echo ================================================
"%PYTHON_PATH%" "%SCRIPT_DIR%auto_uploader.py" "%video_path%" "%platforms%"
pause
goto MENU

:EXIT
echo.
echo 退出程序...
exit /b 0