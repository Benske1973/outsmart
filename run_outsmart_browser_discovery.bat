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

echo READ-ONLY OutSmart Browser Discovery
echo Deze tool opent een aparte browser en scant alleen schermen/dropdowns.
echo Niet op Opslaan, Verwijderen, Aanmaken of Status wijzigen klikken.
echo.
%PYTHON_CMD% outsmart_browser_discovery.py
pause
