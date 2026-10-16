@echo off
rem Liga o modo debug: grava logs\overlay.log (o que o OCR leu) e recortes em debug\
cd /d "%~dp0"
if exist NightreignOverlay.exe (
  start "" "NightreignOverlay.exe" --debug
) else (
  start "" ".venv\Scripts\pythonw.exe" "src\main.py" --debug
)
