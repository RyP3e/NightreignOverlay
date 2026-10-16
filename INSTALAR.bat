@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Nightreign Overlay - Instalacao
cd /d "%~dp0"
echo ==============================================================
echo   NIGHTREIGN OVERLAY - instalacao (cria o .exe nesta pasta)
echo ==============================================================
echo.

rem ---- 1) Python 3.10 a 3.13 -------------------------------------------------
set "PY="
for %%V in (3.12 3.11 3.13 3.10) do (
  if not defined PY (
    py -%%V -c "import tkinter" >nul 2>&1 && set "PY=py -%%V"
  )
)
if not defined PY (
  python -c "import sys,tkinter; assert (3,10)<=sys.version_info[:2]<=(3,13)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [!] Python 3.12 nao encontrado. Tentando instalar com o winget...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo.
  echo Python instalado? FECHE esta janela e execute Instalar.bat de novo.
  echo Se o winget nao existir, baixe o Python 3.12 em python.org ^(marque "tcl/tk"^).
  pause
  exit /b 1
)
echo [1/4] Python encontrado: %PY%

rem ---- 2) ambiente local (tudo dentro desta pasta) --------------------------
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv || goto :erro
)
echo [2/4] Instalando dependencias (precisa de internet)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller || goto :erro

rem ---- 3) gera o executavel NESTA pasta ---------------------------------------
echo [3/4] Criando NightreignOverlay.exe ...
if exist NightreignOverlay.exe del /q NightreignOverlay.exe
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --noconsole ^
  --name NightreignOverlay --icon "%CD%\assets\icon.ico" ^
  --distpath . --workpath build --specpath build --paths src ^
  --collect-all winrt.runtime --collect-all winrt.windows.foundation ^
  --collect-all winrt.windows.foundation.collections --collect-all winrt.windows.globalization ^
  --collect-all winrt.windows.graphics.imaging --collect-all winrt.windows.media.ocr ^
  --collect-all winrt.windows.storage.streams ^
  src\main.py >logs\build.log 2>&1
if exist build rmdir /s /q build
if exist NightreignOverlay.spec del /q NightreignOverlay.spec

rem ---- 4) teste rapido do exe; se falhar, cria atalho alternativo --------------
set "OK=0"
if exist NightreignOverlay.exe (
  start /wait "" "%CD%\NightreignOverlay.exe" --selftest
  if not errorlevel 1 set "OK=1"
)
if "%OK%"=="1" (
  set "TARGET=%CD%\NightreignOverlay.exe"
  set "ARGS="
  echo [4/4] Executavel OK.
) else (
  echo [!] O .exe nao passou no teste ^(veja logs\build.log e logs\selftest.txt^).
  echo     Criando atalho alternativo que roda direto pelo Python local...
  if exist NightreignOverlay.exe del /q NightreignOverlay.exe
  set "TARGET=%CD%\.venv\Scripts\pythonw.exe"
  set "ARGS=%CD%\src\main.py"
)
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%CD%\Nightreign Overlay.lnk'); $s.TargetPath='!TARGET!'; $s.Arguments='!ARGS!'; $s.WorkingDirectory='%CD%'; $s.IconLocation='%CD%\assets\icon.ico'; $s.Save()"

echo.
choice /m "Criar atalho na Area de Trabalho?"
if not errorlevel 2 (
  powershell -NoProfile -Command "$d=[Environment]::GetFolderPath('Desktop'); Copy-Item '%CD%\Nightreign Overlay.lnk' (Join-Path $d 'Nightreign Overlay.lnk') -Force"
)
echo.
echo Pronto! Abra "NightreignOverlay.exe" (ou "Nightreign Overlay.lnk") nesta pasta.
echo O overlay aparece no canto inferior direito. Arraste para mover. Atalhos: F6 F7 F8 F9 F10 F11.
pause
exit /b 0

:erro
echo.
echo [X] Falha na instalacao. Verifique sua internet e tente de novo.
pause
exit /b 1
