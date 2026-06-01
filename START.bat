@echo off
title TOMMY v5
color 0B
echo.
echo ============================================================
echo   TOMMY v5 - Starting
echo ============================================================
echo.
echo Starting TOMMY server...
start /B py -3.11 server.py
timeout /t 2 /nobreak >nul
echo Starting wake word listener...
start /B py -3.11 listener.py
echo.
echo TOMMY is running.  Say "Hey TOMMY" to activate.
echo Close this window to stop TOMMY.
echo.
pause
