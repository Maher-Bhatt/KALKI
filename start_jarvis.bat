@echo off
color 0a
title KALKI System Boot
echo ===================================================
echo  KALKI Initialization Sequence Started...
echo ===================================================
echo.
echo [1/2] Starting KALKI Server on Python 3.11...
start "KALKI Server" "C:\Users\maher\AppData\Local\Programs\Python\Python311\python.exe" server.py
echo.
echo [2/2] Waiting 5 seconds for server to boot, then launching listener...
timeout /t 5 /nobreak > nul
echo.
echo [OK] Starting KALKI Listener (Microphone)...
"C:\Users\maher\AppData\Local\Programs\Python\Python311\python.exe" listener.py
pause
