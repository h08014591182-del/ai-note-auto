@echo off
REM AI Note Auto Poster - 初回セットアップスクリプト
REM 初回のみ実行してください

cd /d "%~dp0"

echo ================================================
echo  AI Note Auto Poster - Setup
echo ================================================
echo.

REM Python確認
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python が見つかりません。
    echo https://www.python.org/downloads/ からPython 3.11以上をインストールしてください。
    echo インストール時に "Add Python to PATH" にチェックを入れてください。
    pause
    exit /b 1
)

python --version
echo.

REM 仮想環境作成
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    echo Done.
)

REM 仮想環境を有効化
call .venv\Scripts\activate.bat

REM 依存パッケージインストール
echo Installing dependencies...
pip install -r requirements.txt
echo Done.

REM Playwrightブラウザのインストール
echo Installing Playwright browsers (Chromium)...
playwright install chromium
echo Done.

REM .envファイルのセットアップ
if not exist ".env" (
    echo.
    echo Creating .env file from template...
    copy .env.example .env
    echo.
    echo [IMPORTANT] Please edit .env file and fill in your credentials:
    echo   - ANTHROPIC_API_KEY: https://console.anthropic.com
    echo   - NOTE_EMAIL: your Note.com email
    echo   - NOTE_PASSWORD: your Note.com password
    notepad .env
)

echo.
echo ================================================
echo  Setup Complete!
echo ================================================
echo.
echo Next steps:
echo 1. Edit .env with your credentials (if not done)
echo 2. Test run: double-click run.bat
echo 3. Schedule daily: run setup_scheduler.bat as Administrator
echo.
pause
