@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
if exist "C:\outsmart\.venv\Scripts\python.exe" set "PYTHON_CMD=C:\outsmart\.venv\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py"
if not defined PYTHON_CMD (
    echo Geen Python gevonden.
    pause
    exit /b 1
)

if "%~2"=="" (
    echo Gebruik:
    echo run_mail_dossier_extract.bat imports\mailbox_export_20260723_090753.zip 4008875 4526006545 2026.4705
    pause
    exit /b 1
)

"%PYTHON_CMD%" extract_mail_dossier.py %*
pause
