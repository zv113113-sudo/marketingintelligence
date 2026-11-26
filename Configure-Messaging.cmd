@echo off
cd /d "%~dp0"
python configure_local.py
if errorlevel 1 pause
