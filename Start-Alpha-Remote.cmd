@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_remote_engine.ps1" %*
set "alpha_remote_exit=%errorlevel%"
echo.
pause
exit /b %alpha_remote_exit%
