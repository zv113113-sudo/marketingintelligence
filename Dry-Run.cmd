@echo off
cd /d "%~dp0"
python run.py --dry-run
echo.
echo Dry run does not send Telegram messages or update normal history.
pause
