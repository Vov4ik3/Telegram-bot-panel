@echo off
setlocal
cd /d "%~dp0.."

echo ===================================
echo  Bot Panel: first-time setup
echo ===================================

if not exist venv\Scripts\python.exe (
    echo [1/2] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create venv. Is Python installed and on PATH?
        pause
        exit /b 1
    )
) else (
    echo [1/2] Virtual environment already exists.
)

echo [2/2] Installing dependencies...
venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Setup complete. Starting the panel now...
call "%~dp0run.bat"
