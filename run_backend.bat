@echo off
REM BeatDrop media engine launcher for Windows
cd /d "%~dp0"

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installing dependencies (first run takes a minute)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

REM Bind to all interfaces so a phone on the same Wi-Fi can reach the engine.
set BEATDROP_HOST=0.0.0.0
set BEATDROP_PORT=5001

echo.
echo ============================================================
echo  BeatDrop engine starting on port 5001
echo  If Windows Firewall prompts, ALLOW access on private nets
echo  Stop with Ctrl+C
echo ============================================================
python app.py
pause
