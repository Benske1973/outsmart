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

if "%~1"=="" (
    echo Geef een scanmap mee, bijvoorbeeld:
    echo run_workorder_scan_extract.bat C:\outsmart\outsmart-main\outsmart_exports\20260723_132921_Werkbon_OutSmart
    pause
    exit /b 1
)

"%PYTHON_CMD%" extract_workorder_scan.py "%~1"
pause
