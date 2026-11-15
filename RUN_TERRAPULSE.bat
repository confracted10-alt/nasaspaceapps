@echo off
setlocal
cd /d "%~dp0"
title TerraPulse Launcher

echo ========================================
echo             TERRAPULSE
echo ========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python was not found.
    echo Install Python 3.12 from https://www.python.org/downloads/
    echo During installation, enable "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating the TerraPulse environment...
    py -3.12 -m venv .venv 2>nul
    if errorlevel 1 py -3.11 -m venv .venv 2>nul
    if errorlevel 1 py -m venv .venv
    if errorlevel 1 (
        echo Could not create the Python environment.
        echo Install Python 3.11 or 3.12, then try again.
        pause
        exit /b 1
    )
)

echo.
echo Installing or checking required packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo Starting TerraPulse...
echo Your browser should open at http://localhost:8501
echo Keep this window open while using TerraPulse.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto error
goto end

:error
echo.
echo TerraPulse could not start. Read the error above.
pause
exit /b 1

:end
pause
