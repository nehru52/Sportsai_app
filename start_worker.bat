@echo off
setlocal
title SportsAI AI-Analysis Worker (Olympic Grade)

echo ==========================================
echo    SportsAI Analysis Worker Starting...
echo ==========================================
echo.
echo [INFO] This worker processes the AI queue (YOLO, Pose, LLM).
echo [INFO] Keep this window open to process incoming videos.
echo.

:: Check for python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    pause
    exit /b
)

:: Run the worker
:: We use -u for unbuffered output so you see logs in real-time
python -u worker.py

echo.
echo ==========================================
echo    Worker has stopped.
echo ==========================================
pause
