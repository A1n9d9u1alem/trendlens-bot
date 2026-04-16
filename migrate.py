"""
Database Migration System
Handles schema changes safely with version tracking
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class DatabaseMigration:
    """Handle database migrations safely"""
    
    def __init__(self):
        self.engine = create_engine(os.getenv('DATABASE_URL'))
        self.migrations = []
        self._register_migrations()
    
    def _register_migrations(self):
        """Register all migrations in order"""
        self.migrations = [
            self.migration_001_add_is_banned,
            self.migration_002_add_language,
            self.migration_003_add_content_hash,
            self.migration_004_add_indexes,
            self.migration_005_add_security_columns,
        ]
    
    def _create_migrations_table(self):
        """Create migrations tracking table"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
    
    def _is_migration_applied(self, migration_name):
        """Check if migration was already applied"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM migrations WHERE migration_name = :name"),
                {"name": migration_name}
            )
            return result.scalar() > 0
    
    def _mark_migration_applied(self, migration_name):
        """Mark migration as applied"""
        with self.engine.connect() as conn:
            conn.execute(
                text("INSERT INTO migrations (migration_name) VALUES (:name)"),
                {"name": migration_name}
            )
            conn.commit()
    
    def _column_exists(self, table_name, column_name):
        """Check if column exists in table"""
        inspector = inspect(self.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    
    def _table_exists(self, table_name):
        """Check if table exists"""
        inspector = inspect(self.engine)
        return table_name in inspector.get_table_names()
    
    # Migration 001: Add is_banned column
    def migration_001_add_is_banned(self):
        """Add is_banned column to users table"""
        if not self._table_exists('users'):
            print("⚠️  Users table doesn't exist yet, skipping...")
            return True
        
        if self._column_exists('users', 'is_banned'):
            print("✅ is_banned column already exists")
            return True
        
        with self.engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN is_banned BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            print("✅ Added is_banned column to users table")
        return True
    
    # Migration 002: Add language column
    def migration_002_add_language(self):
        """Add language column to users table"""
        if not self._table_exists('users'):
            print("⚠️  Users table doesn't exist yet, skipping...")
            return True
        
        if self._column_exists('users', 'language'):
            print("✅ language column already exists")
            return True
        
        with self.engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN language VARCHAR(10) DEFAULT 'en'
            """))
            conn.commit()
            print("✅ Added language column to users table")
        return True
    
    # Migration 003: Add content_hash column
    def migration_003_add_content_hash(self):
        """Add content_hash column to content table"""
        if not self._table_exists('content'):
            print("⚠️  Content table doesn't exist yet, skipping...")
            return True
        
        if self._column_exists('content', 'content_hash'):
            print("✅ content_hash column already exists")
            return True
        
        with self.engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE content 
                ADD COLUMN content_hash VARCHAR(64)
            """))
            conn.commit()
            print("✅ Added content_hash column to content table")
        return True
    
    # Migration 004: Add indexes
    def migration_004_add_indexes(self):
        """Add performance indexes"""
        if not self._table_exists('content'):
            print("⚠️  Content table doesn't exist yet, skipping...")
            return True
        
        with self.engine.connect() as conn:
            # Check if indexes exist
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'content' 
                AND indexname IN ('idx_content_category', 'idx_content_created_at', 'idx_content_trend_score')
            """))
            existing_indexes = [row[0] for row in result]
            
            if 'idx_content_category' not in existing_indexes:
                conn.execute(text("CREATE INDEX idx_content_category ON content(category)"))
                print("✅ Added index on content.category")
            else:
                print("✅ Index on content.category already exists")
            
            if 'idx_content_created_at' not in existing_indexes:
                conn.execute(text("CREATE INDEX idx_content_created_at ON content(created_at)"))
                print("✅ Added index on content.created_at")
            else:
                print("✅ Index on content.created_at already exists")
            
            if 'idx_content_trend_score' not in existing_indexes:
                conn.execute(text("CREATE INDEX idx_content_trend_score ON content(trend_score)"))
                print("✅ Added index on content.trend_score")
            else:
                print("✅ Index on content.trend_score already exists")
            
            conn.commit()
        return True
    
    # Migration 005: Add security columns
    def migration_005_add_security_columns(self):
        """Add security-related columns"""
        if not self._table_exists('users'):
            print("⚠️  Users table doesn't exist yet, skipping...")
            return True
        
        columns_to_add = {
            'last_login': 'TIMESTAMP',
            'login_count': 'INTEGER DEFAULT 0',
            'failed_login_attempts': 'INTEGER DEFAULT 0'
        }
        
        with self.engine.connect() as conn:
            for column_name, column_type in columns_to_add.items():
                if not self._column_exists('users', column_name):
                    conn.execute(text(f"""
                        ALTER TABLE users 
                        ADD COLUMN {column_name} {column_type}
                    """))
                    print(f"✅ Added {column_name} column to users table")
                else:
                    print(f"✅ {column_name} column already exists")
            conn.commit()
        return True
    
    def run_migrations(self):
        """Run all pending migrations"""
        print("=" * 50)
        print("🔄 Database Migration System")
        print("=" * 50)
        
        # Create migrations table
        self._create_migrations_table()
        print("✅ Migrations tracking table ready\n")
        
        # Run each migration
        for migration_func in self.migrations:
            migration_name = migration_func.__name__
            
            print(f"📋 Checking: {migration_name}")
            
            if self._is_migration_applied(migration_name):
                print(f"⏭️  Already applied: {migration_name}\n")
                continue
            
            try:
                print(f"🔄 Running: {migration_name}")
                success = migration_func()
                
                if success:
                    self._mark_migration_applied(migration_name)
                    print(f"✅ Completed: {migration_name}\n")
                else:
                    print(f"❌ Failed: {migration_name}\n")
                    return False
            except Exception as e:
                print(f"❌ Error in {migration_name}: {e}\n")
                return False
        
        print("=" * 50)
        print("✅ All migrations completed successfully!")
        print("=" * 50)
        return True
    
    def rollback_migration(self, migration_name):
        """Rollback a specific migration (manual process)"""
        print(f"⚠️  Manual rollback required for: {migration_name}")
        print("Please review the migration and manually revert changes if needed.")
    
    def list_migrations(self):
        """List all migrations and their status"""
        print("=" * 50)
        print("📋 Migration Status")
        print("=" * 50)
        
        self._create_migrations_table()
        
        for migration_func in self.migrations:
            migration_name = migration_func.__name__
            applied = self._is_migration_applied(migration_name)
            status = "✅ Applied" if applied else "⏳ Pending"
            print(f"{status} - {migration_name}")
        
        print("=" * 50)


def main():
    """Main entry point"""
    import sys
    
    migrator = DatabaseMigration()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            migrator.list_migrations()
        elif command == "run":
            migrator.run_migrations()
        else:
            print("Usage: python migrate.py [list|run]")
    else:
        # Default: run migrations
        migrator.run_migrations()


if __name__ == '__main__':
    main()
