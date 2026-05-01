@echo off
REM AI Note Auto Poster - 実行スクリプト
cd /d "%~dp0"

echo [%date% %time%] Starting AI Note Auto Poster...
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py"

if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] ERROR: Script failed with exit code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo [%date% %time%] Completed successfully.
