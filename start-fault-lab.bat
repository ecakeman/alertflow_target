@echo off
rem One-click launcher for Fault Lab. Double-click, or run from a terminal.
rem Any arguments are passed through to start-fault-lab.ps1
rem   e.g.  start-fault-lab.bat -Port 9000 -Dev
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-fault-lab.ps1" %*
if errorlevel 1 pause
endlocal
