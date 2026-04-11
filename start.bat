@echo off
echo Starting SportsAI...
echo.
echo API will be at: http://localhost:8001
echo Frontend will be at: http://localhost:3000
echo.

start "SportsAI API" cmd /k "cd /d C:\sportsai-backend && uvicorn api:app --host 0.0.0.0 --port 8001"
timeout /t 3 /nobreak >nul
start "SportsAI Frontend" cmd /k "python -m http.server 3000 --directory C:\sportsai-backend\frontend"
timeout /t 2 /nobreak >nul
start "" "http://localhost:3000"

echo Both servers started. Browser opening...
