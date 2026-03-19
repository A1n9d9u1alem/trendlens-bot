"""Add notification system tables and columns"""
from database import SessionLocal, engine, Base
from sqlalchemy import text

db = SessionLocal()

try:
    print("Adding notification columns to users...")
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_enabled BOOLEAN DEFAULT TRUE"))
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_frequency VARCHAR(20) DEFAULT 'hourly'"))
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_categories TEXT"))
    db.commit()
    print("User columns added!")
    
    print("\nCreating notification_logs table...")
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS notification_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            content_id INTEGER REFERENCES content(id),
            status VARCHAR(20) DEFAULT 'pending',
            sent_at TIMESTAMP,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_notif_user_status ON notification_logs(user_id, status)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_notif_created ON notification_logs(created_at DESC)"))
    db.commit()
    print("Notification logs table created!")
    
    print("\nNotification system ready!")
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
