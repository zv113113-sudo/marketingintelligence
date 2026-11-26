@echo off
cd /d "%~dp0"
"C:\Users\0\AppData\Local\Programs\Python\Python313\python.exe" "%~dp0Check-Telegram-Connection.py"
if errorlevel 1 pause
