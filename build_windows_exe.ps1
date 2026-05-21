$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "Installing GUI packaging dependencies..."
python -m pip install --upgrade pip
python -m pip install pyinstaller matplotlib pyyaml reportlab

Write-Host "Building Windows GUI executable..."
python -m PyInstaller `
  --noconfirm `
  --windowed `
  --name AirportWeatherProfiler `
  --add-data "configs;configs" `
  --add-data "sample_local.csv;." `
  AirportWeatherProfiler.pyw

Write-Host "Done. Open dist\AirportWeatherProfiler\AirportWeatherProfiler.exe"
