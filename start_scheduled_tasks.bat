@echo off
chcp 65001 >nul
echo ============================================
echo   ChinaBound Travel - 启动定时任务
echo ============================================
echo.

cd /d E:\AI\dulizhan\travel-blog

echo [1/2] 启动 Buffer 社交媒体定时发帖...
start "Buffer Scheduler" /min python chinaboundtravel_social_bot\buffer_scheduler.py
timeout /t 2 >nul

echo [2/2] 启动 AI 内容管线...
start "AI Pipeline" /min python agent_pipeline.py
timeout /t 2 >nul

echo.
echo ============================================
echo   所有定时任务已启动！
echo ============================================
echo.
echo 运行中的任务：
echo   - Buffer Scheduler (社交媒体定时发帖)
echo   - AI Pipeline (AI 内容生成)
echo.
echo [INFO] 每日巡检已移至 GitHub Actions 云端运行 (每天 09:30 Beijing)
echo [INFO] 博客生成已移至 GitHub Actions 云端运行 (周一至周五 21:00 Beijing)
echo.
echo 按任意键退出...
pause >nul
