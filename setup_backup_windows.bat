@echo off
REM Setup daily backup on Windows using Task Scheduler

set SCRIPT_PATH=%~dp0backup.py
set PYTHON_PATH=python

echo Creating scheduled task for daily backup at 2 AM...

schtasks /create /tn "TrendLens_Daily_Backup" /tr "%PYTHON_PATH% %SCRIPT_PATH%" /sc daily /st 02:00 /f

if %errorlevel% equ 0 (
    echo ✅ Backup task created successfully!
    echo Task will run daily at 2:00 AM
    echo.
    echo To view: schtasks /query /tn "TrendLens_Daily_Backup"
    echo To delete: schtasks /delete /tn "TrendLens_Daily_Backup" /f
) else (
    echo ❌ Failed to create task. Run as Administrator.
)

pause
