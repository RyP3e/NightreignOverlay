@echo off
rem Uso: Testar_Print.bat "C:\caminho\print.png"  -> mostra o que o OCR enxerga naquele print
cd /d "%~dp0"
if "%~1"=="" (echo Arraste um print para cima deste arquivo, ou passe o caminho. & pause & exit /b)
".venv\Scripts\python.exe" tools\testar_imagem.py "%~1"
pause
