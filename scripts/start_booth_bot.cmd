@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_booth_bot.ps1" %*
set "alpha_bot_exit=%errorlevel%"
echo.
pause
exit /b %alpha_bot_exit%
