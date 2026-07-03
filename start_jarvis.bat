@echo off
color 0a
title KALKI System Boot
echo ===================================================
echo  KALKI Initialization Sequence Started...
echo ===================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

echo [1/2] Starting KALKI Server...
start "KALKI Server" python server.py
echo.
echo [2/2] Waiting 5 seconds for server to boot, then launching listener...
timeout /t 5 /nobreak > nul
echo.
echo [OK] Starting KALKI Listener (Microphone)...
python listener.py
pause
