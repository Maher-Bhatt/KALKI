@echo off
title KALKI v1.0.4 PRO
color 0B
echo.
echo ============================================================
echo   KALKI v1.0.4 PRO - Starting
echo ============================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

echo Starting KALKI server...
start /B python server.py
timeout /t 2 /nobreak >nul
echo Starting wake word listener...
start /B python listener.py
echo.
echo KALKI is running.  Say "Hey KALKI" to activate.
echo Close this window to stop KALKI.
echo.
pause
