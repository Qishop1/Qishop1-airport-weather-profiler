@echo off
cd /d "%~dp0"
pythonw AirportWeatherProfiler.pyw
if errorlevel 1 (
  python AirportWeatherProfiler.pyw
  pause
)
