"""Add language column to users table"""
from database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(5) DEFAULT 'en'"))
    db.commit()
    print("Language column added successfully")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
