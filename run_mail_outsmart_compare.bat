@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
if not defined PYTHON_CMD if defined VIRTUAL_ENV if exist "%VIRTUAL_ENV%\Scripts\python.exe" set "PYTHON_CMD=%VIRTUAL_ENV%\Scripts\python.exe"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py"
if not defined PYTHON_CMD (
    echo Geen Python gevonden.
    pause
    exit /b 1
)

if "%~1"=="" (
    echo Geef het mailbox ZIP-bestand mee, bijvoorbeeld:
    echo run_mail_outsmart_compare.bat imports\mailbox_export_20260723_090753.zip
    echo.
    echo Zet OutSmart CSV exports in imports\outsmart\
    pause
    exit /b 1
)

%PYTHON_CMD% compare_mail_to_outsmart.py "%~1" --outsmart-dir imports\outsmart
pause
