"""Add content_hash column for deduplication"""
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    print("Adding content_hash column...")
    db.execute(text("ALTER TABLE content ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_content_hash ON content(content_hash)"))
    db.commit()
    print("Column added successfully!")
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
