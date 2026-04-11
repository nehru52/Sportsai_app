@echo off
echo ========================================
echo SportsAI - Public URL Setup
echo ========================================
echo.
echo Starting tunnels...
echo.

start "Frontend Server" cmd /k "cd frontend && python -m http.server 3000"
timeout /t 3 /nobreak >nul

start "Backend Server" cmd /k "cd .. && python -m uvicorn api:app --host 0.0.0.0 --port 8001"
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo Local URLs (same network):
echo Frontend: http://192.168.0.17:3000
echo Backend:  http://192.168.0.17:8001
echo ========================================
echo.
echo Share the Frontend URL with your cousin if they're on the same WiFi
echo.
pause
