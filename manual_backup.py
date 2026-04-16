"""
Manual Database Backup Script
Run this to create an immediate backup
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from auto_backup import DatabaseBackup

load_dotenv()


def main():
    print("=" * 50)
    print("Database Backup Tool")
    print("=" * 50)
    print()
    
    backup = DatabaseBackup()
    
    print("Options:")
    print("1. Create new backup")
    print("2. List all backups")
    print("3. Restore from backup")
    print("4. Exit")
    print()
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == '1':
        print("\n📦 Creating backup...")
        result = backup.create_backup()
        if result:
            print(f"\n✅ Backup created: {result}")
        else:
            print("\n❌ Backup failed!")
    
    elif choice == '2':
        print()
        backup.list_backups()
    
    elif choice == '3':
        print()
        backups = backup.list_backups()
        if not backups:
            print("❌ No backups available")
            return
        
        print("\nEnter backup number to restore (or 0 to cancel):")
        for i, b in enumerate(backups, 1):
            print(f"{i}. {b}")
        
        try:
            num = int(input("\nChoice: ").strip())
            if num == 0:
                print("Cancelled")
                return
            
            if 1 <= num <= len(backups):
                backup_file = os.path.join(backup.backup_dir, backups[num-1])
                confirm = input(f"\n⚠️ Restore from {backups[num-1]}? This will overwrite current data! (yes/no): ")
                
                if confirm.lower() == 'yes':
                    print("\n🔄 Restoring...")
                    if backup.restore_backup(backup_file):
                        print("✅ Restore completed!")
                    else:
                        print("❌ Restore failed!")
                else:
                    print("Cancelled")
            else:
                print("Invalid choice")
        except ValueError:
            print("Invalid input")
    
    elif choice == '4':
        print("Goodbye!")
        sys.exit(0)
    
    else:
        print("Invalid choice")


if __name__ == '__main__':
    main()
