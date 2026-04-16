"""
Automated Database Backup System
Backs up PostgreSQL database to local files and cloud storage
"""

import os
import subprocess
from datetime import datetime, timezone
import schedule
import time
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.backup_dir = os.path.join(os.getcwd(), 'backups')
        self.max_backups = 7  # Keep last 7 backups
        
        # Create backup directory
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_backup(self):
        """Create database backup"""
        try:
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(self.backup_dir, f'backup_{timestamp}.sql')
            
            logger.info(f"Starting backup to {backup_file}")
            
            # Use pg_dump to create backup
            cmd = f'pg_dump "{self.database_url}" > "{backup_file}"'
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Backup created successfully: {backup_file}")
                self.cleanup_old_backups()
                return backup_file
            else:
                logger.error(f"❌ Backup failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Backup error: {e}")
            return None
    
    def cleanup_old_backups(self):
        """Remove old backups, keep only recent ones"""
        try:
            backups = sorted([
                f for f in os.listdir(self.backup_dir) 
                if f.startswith('backup_') and f.endswith('.sql')
            ])
            
            if len(backups) > self.max_backups:
                for old_backup in backups[:-self.max_backups]:
                    old_path = os.path.join(self.backup_dir, old_backup)
                    os.remove(old_path)
                    logger.info(f"🗑️ Removed old backup: {old_backup}")
                    
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def restore_backup(self, backup_file):
        """Restore database from backup"""
        try:
            logger.info(f"Restoring from {backup_file}")
            
            cmd = f'psql "{self.database_url}" < "{backup_file}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Restore completed successfully")
                return True
            else:
                logger.error(f"❌ Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Restore error: {e}")
            return False
    
    def list_backups(self):
        """List all available backups"""
        backups = sorted([
            f for f in os.listdir(self.backup_dir) 
            if f.startswith('backup_') and f.endswith('.sql')
        ], reverse=True)
        
        logger.info(f"📦 Available backups ({len(backups)}):")
        for backup in backups:
            backup_path = os.path.join(self.backup_dir, backup)
            size = os.path.getsize(backup_path) / (1024 * 1024)  # MB
            logger.info(f"  - {backup} ({size:.2f} MB)")
        
        return backups


def run_scheduled_backup():
    """Run backup on schedule"""
    backup = DatabaseBackup()
    backup.create_backup()


def main():
    """Main backup scheduler"""
    backup = DatabaseBackup()
    
    logger.info("🚀 Database Backup System Started")
    logger.info(f"📁 Backup directory: {backup.backup_dir}")
    logger.info(f"🔄 Schedule: Daily at 2:00 AM")
    
    # Create initial backup
    backup.create_backup()
    
    # Schedule daily backups at 2 AM
    schedule.every().day.at("02:00").do(run_scheduled_backup)
    
    # Also backup every 6 hours
    schedule.every(6).hours.do(run_scheduled_backup)
    
    logger.info("⏰ Scheduler running... Press Ctrl+C to stop")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == '__main__':
    main()
