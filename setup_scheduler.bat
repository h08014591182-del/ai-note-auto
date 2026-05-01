@echo off
REM Windows Task Schedulerで毎朝8:00に自動実行するタスクを登録する
REM 管理者権限で実行してください

set TASK_NAME=AI-Note-Auto-Poster
set SCRIPT_PATH=%~dp0run.bat
set HOUR=08
set MINUTE=00

echo Creating scheduled task: %TASK_NAME%
echo Script: %SCRIPT_PATH%
echo Time: %HOUR%:%MINUTE% daily

schtasks /create /tn "%TASK_NAME%" /tr "\"%SCRIPT_PATH%\"" /sc daily /st %HOUR%:%MINUTE% /f

if %ERRORLEVEL% == 0 (
    echo.
    echo [SUCCESS] Task scheduled successfully!
    echo The script will run daily at %HOUR%:%MINUTE%.
    echo.
    echo To verify: schtasks /query /tn "%TASK_NAME%"
    echo To delete:  schtasks /delete /tn "%TASK_NAME%" /f
) else (
    echo.
    echo [ERROR] Failed to create task. Please run as Administrator.
)

pause
