@echo off
cd /d "%~dp0"
pythonw AirportWeatherProfiler.pyw
if errorlevel 1 (
  echo.
  echo Python GUI failed to start. Trying normal Python so the error remains visible...
  python AirportWeatherProfiler.pyw
  pause
)
