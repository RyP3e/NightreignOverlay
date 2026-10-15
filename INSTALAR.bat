@echo off
setlocal
chcp 65001 >nul
title Nightreign Overlay - Instalador
cd /d "%~dp0"
echo ==============================================
echo    NIGHTREIGN OVERLAY - Instalacao
echo ==============================================
echo.

rem O leitor de texto (onnxruntime) so tem pacote para Python 3.10 a 3.13.
set "PY="
call :try "py -3.12"
call :try "py -3.11"
call :try "py -3.13"
call :try "py -3.10"
call :try "python"

if not defined PY (
  echo Nao encontrei um Python compativel ^(3.10 a 3.13^).
  echo Instalando o Python 3.12...
  where py >nul 2>&1
  if not errorlevel 1 py install 3.12
  call :try "py -3.12"
)
if not defined PY (
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  call :try "py -3.12"
  call :try "python"
)
if not defined PY (
  echo.
  echo Nao consegui deixar um Python compativel pronto automaticamente.
  echo 1^) Instale o Python 3.12 em: https://www.python.org/downloads/release/python-3129/
  echo    ^(marque "Add python.exe to PATH"^)
  echo 2^) Feche esta janela e rode INSTALAR.bat de novo.
  pause
  exit /b 1
)

echo Usando: %PY%
%PY% --version
echo.
echo [1/3] Instalando dependencias (pode demorar alguns minutos)...
%PY% -m pip install --upgrade pip >nul 2>&1
%PY% -m pip install -r "%~dp0requirements.txt"
%PY% -c "import rapidocr_onnxruntime, mss, cv2, numpy, PyInstaller" >nul 2>&1
if errorlevel 1 goto :erro

echo.
echo [2/3] Gerando NightreignOverlay.exe nesta pasta...
set "ICON="
if exist "%~dp0icon.ico" set "ICON=--icon "%~dp0icon.ico""
%PY% -m PyInstaller --noconfirm --clean --onefile --noconsole --name NightreignOverlay %ICON% --distpath "%~dp0." --workpath "%TEMP%\nr_build" --specpath "%TEMP%\nr_build" --paths "%~dp0." --collect-all rapidocr_onnxruntime "%~dp0NightreignOverlay.py"
if not exist "%~dp0NightreignOverlay.exe" goto :erro
rmdir /s /q "%TEMP%\nr_build" >nul 2>&1

echo.
echo [3/3] Pronto!
echo.
echo   O arquivo NightreignOverlay.exe foi criado NESTA pasta.
echo   De dois cliques nele para abrir o overlay.
echo.
set /p RUN="Abrir agora? (S/N): "
if /i "%RUN%"=="S" start "" "%~dp0NightreignOverlay.exe"
exit /b 0

:erro
echo.
echo Ocorreu um erro na instalacao. Verifique sua internet e tente de novo.
echo Se persistir, tire print desta janela e envie.
pause
exit /b 1

rem ---- testa se o comando e um Python 3.10 a 3.13 de verdade ----
:try
if defined PY goto :eof
set "CAND=%~1"
set "VER="
for /f "delims=" %%i in ('%CAND% -c "import sys;print(sys.version_info[0]*100+sys.version_info[1])" 2^>nul') do set "VER=%%i"
if not defined VER goto :eof
echo %VER%| findstr /r "^31[0-3]$" >nul
if not errorlevel 1 set "PY=%CAND%"
goto :eof
