
@echo off
title AGROVISION Dashboard
cd /d "%~dp0"

echo ==========================================
echo       AGROVISION - Starting Server
echo ==========================================

start "AGROVISION Server" cmd /k "cd /d ""%~dp0"" && py web\app.py"

echo Waiting for server to start...
timeout /t 8 /nobreak >nul

start "" "http://127.0.0.1:5000/dashboard"

exit
