@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File build_windows_exe.ps1
pause
