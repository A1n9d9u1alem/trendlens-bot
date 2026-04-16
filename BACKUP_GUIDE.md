# Database Backup Automation

## ✅ Features

- **Automated Backups**: Runs every 6 hours + daily at 2 AM
- **Local Storage**: Saves backups to `backups/` folder
- **Auto Cleanup**: Keeps last 7 backups, deletes older ones
- **Manual Backup**: Create backups on-demand
- **Easy Restore**: Restore from any backup file

## 🚀 Quick Start

### Option 1: Automated Backups (Recommended)

**Windows:**
```bash
# Double-click or run:
start_backup.bat
```

**Linux/Mac:**
```bash
python auto_backup.py
```

This will:
- Create immediate backup
- Schedule backups every 6 hours
- Schedule daily backup at 2 AM
- Keep running in background

### Option 2: Manual Backup

```bash
python manual_backup.py
```

Choose from menu:
1. Create new backup
2. List all backups
3. Restore from backup

## 📋 Requirements

Install dependencies:
```bash
pip install schedule psycopg2-binary python-dotenv
```

**For Windows:** Install PostgreSQL tools:
- Download from: https://www.postgresql.org/download/windows/
- Or use: `choco install postgresql`

**For Linux:**
```bash
sudo apt-get install postgresql-client
```

## 📁 Backup Files

Backups are saved to: `backups/backup_YYYYMMDD_HHMMSS.sql`

Example:
```
backups/
├── backup_20240115_020000.sql  (2.5 MB)
├── backup_20240115_080000.sql  (2.6 MB)
├── backup_20240115_140000.sql  (2.7 MB)
└── backup_20240115_200000.sql  (2.8 MB)
```

## 🔄 Restore Database

### Method 1: Using Manual Script
```bash
python manual_backup.py
# Choose option 3
```

### Method 2: Command Line
```bash
psql "your_database_url" < backups/backup_20240115_020000.sql
```

## ⚙️ Configuration

Edit `auto_backup.py`:

```python
self.max_backups = 7  # Keep last 7 backups
```

Change schedule in `auto_backup.py`:
```python
# Daily at 2 AM
schedule.every().day.at("02:00").do(run_scheduled_backup)

# Every 6 hours
schedule.every(6).hours.do(run_scheduled_backup)

# Every hour (more frequent)
schedule.every().hour.do(run_scheduled_backup)
```

## 🔐 Security

**Backup files contain sensitive data!**

1. **Encrypt backups** (recommended):
```bash
# Encrypt
gpg -c backups/backup_20240115_020000.sql

# Decrypt
gpg backups/backup_20240115_020000.sql.gpg
```

2. **Secure storage**:
- Don't commit backups to Git
- Store in secure location
- Use cloud storage with encryption

3. **Add to .gitignore**:
```
backups/
*.sql
*.sql.gpg
```

## ☁️ Cloud Backup (Optional)

### Upload to AWS S3:
```python
import boto3

s3 = boto3.client('s3')
s3.upload_file(
    backup_file,
    'your-bucket-name',
    f'backups/{os.path.basename(backup_file)}'
)
```

### Upload to Google Drive:
```python
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

gauth = GoogleAuth()
drive = GoogleDrive(gauth)

file = drive.CreateFile({'title': os.path.basename(backup_file)})
file.SetContentFile(backup_file)
file.Upload()
```

## 🐛 Troubleshooting

**Error: pg_dump not found**
- Install PostgreSQL client tools
- Add to PATH: `C:\Program Files\PostgreSQL\16\bin`

**Error: Permission denied**
- Run as administrator (Windows)
- Check database credentials in .env

**Backup file is 0 KB**
- Check DATABASE_URL is correct
- Verify database connection
- Check disk space

## 📊 Monitoring

Check backup status:
```bash
python manual_backup.py
# Choose option 2 to list backups
```

View backup logs:
- Check console output
- Logs show: timestamp, file size, status

## 🔄 Automation Options

### Windows Task Scheduler:
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 2 AM
4. Action: Start program `python.exe`
5. Arguments: `auto_backup.py`
6. Start in: `C:\path\to\trendlens-bot`

### Linux Cron:
```bash
# Edit crontab
crontab -e

# Add line (runs at 2 AM daily)
0 2 * * * cd /path/to/trendlens-bot && python auto_backup.py
```

### Docker:
```dockerfile
# Add to Dockerfile
RUN apt-get install -y postgresql-client

# Add to docker-compose.yml
services:
  backup:
    build: .
    command: python auto_backup.py
    volumes:
      - ./backups:/app/backups
```

## 📈 Best Practices

1. **Test restores regularly** - Verify backups work
2. **Monitor backup size** - Ensure backups are complete
3. **Keep multiple copies** - Local + cloud storage
4. **Automate verification** - Check backup integrity
5. **Document procedures** - Train team on restore process

## 🆘 Emergency Restore

If database is corrupted:

1. **Stop the bot**:
```bash
# Press Ctrl+C or kill process
```

2. **Restore latest backup**:
```bash
python manual_backup.py
# Choose option 3, select latest backup
```

3. **Verify data**:
```bash
# Check database
psql "your_database_url"
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM content;
```

4. **Restart bot**:
```bash
python bot.py
```

## 📞 Support

If backups fail:
1. Check logs for errors
2. Verify database connection
3. Check disk space
4. Test manual backup
5. Contact admin if issues persist
