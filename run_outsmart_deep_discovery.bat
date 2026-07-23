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

echo OutSmart Deep Discovery - READ-ONLY
echo.
echo 1. Start eerst start_chrome_debug_outsmart.bat
echo 2. Log in op OutSmart in die Chrome
echo 3. Open Nieuwe werkbon of een bestaande werkbon
echo 4. Typ in het zwarte venster: deep
echo.
echo De tool leest velden, frames, tabellen, scrollposities en veilige dropdowns.
echo Hij klikt NIET op opslaan, aanmaken, verwijderen, versturen of status aanpassen.
echo.
"%PYTHON_CMD%" outsmart_attach_discovery.py
pause
