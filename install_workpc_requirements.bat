@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py"
if not defined PYTHON_CMD (
    echo Geen Python gevonden.
    pause
    exit /b 1
)

echo Gebruik Python: %PYTHON_CMD%
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r requirements.txt
%PYTHON_CMD% -m playwright install chromium
pause
