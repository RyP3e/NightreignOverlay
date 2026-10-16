@echo off
cd /d "%~dp0"
if exist NightreignOverlay.exe (
  start "" "NightreignOverlay.exe"
) else (
  start "" ".venv\Scripts\pythonw.exe" "src\main.py"
)
