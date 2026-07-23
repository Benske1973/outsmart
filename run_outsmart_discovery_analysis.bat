@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

set "ZIP=%~1"
if "%ZIP%"=="" set "ZIP=imports\20260723_114121_Werkbon_OutSmart.zip"

echo OutSmart discovery ZIP-analyse
echo Bron: %ZIP%
echo.
"%PYTHON%" analyze_outsmart_discovery.py "%ZIP%"

echo.
pause
