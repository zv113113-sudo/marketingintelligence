@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0daily_run.ps1"
echo.
echo Manual delivery run finished.
pause
