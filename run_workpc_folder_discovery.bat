@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
    goto :run
)

if defined VIRTUAL_ENV (
    if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
        set "PYTHON_CMD=%VIRTUAL_ENV%\Scripts\python.exe"
        goto :run
    )
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYTHON_CMD=python"
    goto :run
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYTHON_CMD=py"
    goto :run
)

echo Geen Python gevonden.
pause
exit /b 1

:run
echo READ-ONLY Outlook folder discovery
echo Er worden geen mails gewijzigd, verplaatst, gelezen gemarkeerd of verwijderd.
echo.
echo Gebruik Python: %PYTHON_CMD%
%PYTHON_CMD% discover_outlook_folders.py
pause
