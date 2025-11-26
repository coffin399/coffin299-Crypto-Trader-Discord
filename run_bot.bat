@echo off
setlocal

REM Check for Python 3.11
py -3.11 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python 3.11 is not installed or not found in PATH.
    echo Please install Python 3.11 and try again.
    pause
    exit /b 1
)

REM Check if venv exists
if not exist .venv (
    echo Creating virtual environment with Python 3.11...
    py -3.11 -m venv .venv
    if %errorlevel% neq 0 (
        echo Error: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate venv
call .venv\Scripts\activate

REM Install requirements
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies.
    pause
    exit /b 1
)

REM Run the bot
echo Starting Coffin299 Crypto Trader...
python web/server.py

pause
