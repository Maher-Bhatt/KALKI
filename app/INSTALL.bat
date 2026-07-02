@echo off
title KALKI v1 PRO - Installer
color 0B
echo.
echo ============================================================
echo   KALKI v1 PRO - Installing Dependencies
echo ============================================================
echo.
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
echo.
echo Installing Chromium for the deep website scanner (optional)...
py -3.11 -m playwright install chromium
echo.
echo ============================================================
echo   Done!  Now do this:
echo   1. Open config.py in Notepad
echo   2. Paste your Groq API key (get free at console.groq.com)
echo   3. Run START.bat
echo ============================================================
echo.
pause
