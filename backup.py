#!/usr/bin/env python3
"""
Database Backup Script for TrendLens Bot
Run daily via cron: 0 2 * * * python backup.py
"""

import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BACKUP_DIR = os.getenv('BACKUP_DIR', './backups')
DATABASE_URL = os.getenv('DATABASE_URL')
MAX_BACKUPS = 7  # Keep last 7 days

def backup_database():
    """Backup PostgreSQL database"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"{BACKUP_DIR}/trendlens_backup_{timestamp}.sql"
    
    print(f"Starting backup: {backup_file}")
    
    try:
        # Use pg_dump
        subprocess.run([
            'pg_dump',
            DATABASE_URL,
            '-f', backup_file,
            '--no-owner',
            '--no-acl'
        ], check=True)
        
        # Compress
        subprocess.run(['gzip', backup_file], check=True)
        print(f"✅ Backup completed: {backup_file}.gz")
        
        # Cleanup old backups
        cleanup_old_backups()
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False
    
    return True

def cleanup_old_backups():
    """Remove old backup files"""
    try:
        backups = sorted([
            f for f in os.listdir(BACKUP_DIR) 
            if f.startswith('trendlens_backup_') and f.endswith('.gz')
        ])
        
        if len(backups) > MAX_BACKUPS:
            for old_backup in backups[:-MAX_BACKUPS]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
                print(f"🗑️  Removed old backup: {old_backup}")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

def restore_database(backup_file):
    """Restore database from backup"""
    if not os.path.exists(backup_file):
        print(f"❌ Backup file not found: {backup_file}")
        return False
    
    try:
        # Decompress if needed
        if backup_file.endswith('.gz'):
            subprocess.run(['gunzip', backup_file], check=True)
            backup_file = backup_file[:-3]
        
        # Restore
        subprocess.run([
            'psql',
            DATABASE_URL,
            '-f', backup_file
        ], check=True)
        
        print(f"✅ Database restored from: {backup_file}")
        return True
        
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        if len(sys.argv) < 3:
            print("Usage: python backup.py restore <backup_file>")
            sys.exit(1)
        restore_database(sys.argv[2])
    else:
        backup_database()
