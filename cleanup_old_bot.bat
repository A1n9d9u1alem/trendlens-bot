@echo off
REM Cleanup Script - Remove Old Bot Files
REM This script backs up and removes the old monolithic bot files

echo ========================================
echo Old Bot Cleanup Script
echo ========================================
echo.

REM Create backup directory with timestamp
set timestamp=%date:~-4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =0%
set backup_dir=old_bot_backup_%timestamp%

echo Creating backup directory: %backup_dir%
mkdir %backup_dir%

echo.
echo Backing up old bot files...

REM Backup old bot files
if exist bot.py (
    echo - Backing up bot.py
    copy bot.py %backup_dir%\bot.py
) else (
    echo - bot.py not found
)

if exist bot_old_backup.py (
    echo - Backing up bot_old_backup.py
    copy bot_old_backup.py %backup_dir%\bot_old_backup.py
) else (
    echo - bot_old_backup.py not found
)

echo.
echo ========================================
echo Backup Complete!
echo ========================================
echo Backup location: %backup_dir%
echo.

REM Ask for confirmation before deletion
echo.
echo WARNING: About to delete old bot files!
echo.
echo Files to be deleted:
if exist bot.py echo   - bot.py
if exist bot_old_backup.py echo   - bot_old_backup.py
echo.
set /p confirm="Are you sure you want to delete these files? (yes/no): "

if /i "%confirm%"=="yes" (
    echo.
    echo Deleting old bot files...
    
    if exist bot.py (
        del bot.py
        echo - Deleted bot.py
    )
    
    if exist bot_old_backup.py (
        del bot_old_backup.py
        echo - Deleted bot_old_backup.py
    )
    
    echo.
    echo ========================================
    echo Cleanup Complete!
    echo ========================================
    echo.
    echo Old bot files have been removed.
    echo Backup saved in: %backup_dir%
    echo.
    echo Your new modular bot is ready to use!
    echo Run: python main.py
    echo.
) else (
    echo.
    echo Cleanup cancelled. No files were deleted.
    echo Backup is still available in: %backup_dir%
    echo.
)

pause
