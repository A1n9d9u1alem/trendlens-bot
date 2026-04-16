@echo off
echo Starting Database Backup Service...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install required packages
echo Installing required packages...
pip install schedule psycopg2-binary python-dotenv

REM Create backups directory
if not exist "backups" mkdir backups

echo.
echo ========================================
echo Database Backup Service
echo ========================================
echo.
echo Schedule:
echo - Every 6 hours
echo - Daily at 2:00 AM
echo.
echo Backups saved to: %cd%\backups
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

REM Run the backup script
python auto_backup.py

pause
