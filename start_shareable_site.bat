@echo off
setlocal
title SportsAI Shareable Website Launcher

echo ==========================================
echo    SportsAI Shareable Website Launcher
echo ==========================================
echo.

:: Check for python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python.
    pause
    exit /b
)

:: Start the Web Server in a new window
echo [1/2] Starting Web Server on port 8080...
start "SportsAI Backend" cmd /k "python complete_web_server.py"

:: Wait a few seconds for server to initialize
timeout /t 5 /nobreak >nul

:: Start Ngrok in a new window
echo [2/2] Starting Ngrok Tunnel...
if exist "ngrok\ngrok.exe" (
    start "SportsAI Ngrok" cmd /k "ngrok\ngrok.exe start --config=ngrok.yml sportsai"
) else (
    echo [WARNING] ngrok\ngrok.exe not found. Trying global ngrok...
    start "SportsAI Ngrok" cmd /k "ngrok start --config=ngrok.yml sportsai"
)

echo.
echo ==========================================
echo    DONE! YOUR WEBSITE IS STARTING...
echo ==========================================
echo.
echo 1. Look at the Ngrok window for the "Forwarding" URL.
echo    It will look like: https://xxxx-xxxx.ngrok-free.app
echo.
echo 2. Open that URL in your browser to test it.
echo.
echo 3. Share that URL with anyone!
echo.
echo NOTE: Keep these windows open while sharing.
echo ==========================================
echo.
pause
