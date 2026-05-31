@echo off
chcp 65001 >nul
echo ============================================
echo   ChinaBound Travel - 启动定时任务
echo ============================================
echo.

cd /d E:\AI\dulizhan\travel-blog

echo [1/3] 启动 Buffer 社交媒体定时发帖...
start "Buffer Scheduler" /min python chinaboundtravel_social_bot\buffer_scheduler.py
timeout /t 2 >nul

echo [2/3] 启动每日巡检任务...
start "Daily Inspector" /min python boundtravel_daily_inspector.py
timeout /t 2 >nul

echo [3/3] 启动 AI 内容管线...
start "AI Pipeline" /min python agent_pipeline.py
timeout /t 2 >nul

echo.
echo ============================================
echo   所有定时任务已启动！
echo ============================================
echo.
echo 运行中的任务：
echo   - Buffer Scheduler (社交媒体定时发帖)
echo   - Daily Inspector (每日巡检)
echo   - AI Pipeline (AI 内容生成)
echo.
echo 按任意键退出...
pause >nul
