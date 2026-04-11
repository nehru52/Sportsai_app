@echo off
echo Starting ngrok tunnels...
echo.
echo IMPORTANT: You need to sign up for a free ngrok account first!
echo 1. Go to: https://dashboard.ngrok.com/signup
echo 2. Sign up (it's free)
echo 3. Copy your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken
echo 4. Run: ngrok config add-authtoken YOUR_TOKEN_HERE
echo.
echo After that, run this batch file again.
echo.
pause

start "Ngrok Frontend" cmd /k "ngrok http 3000"
timeout /t 2 /nobreak >nul
start "Ngrok Backend" cmd /k "ngrok http 8001"

echo.
echo Ngrok tunnels started!
echo Check the terminal windows for your public URLs
echo.
pause
