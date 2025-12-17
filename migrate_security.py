import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def migrate_database():
    engine = create_engine(os.getenv('DATABASE_URL'))
    
    with engine.connect() as conn:
        try:
            # Add is_banned column
            conn.execute(text("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE"))
            print("✅ Added is_banned column")
        except Exception as e:
            print(f"⚠️ is_banned column: {e}")
        
        try:
            # Add last_request column
            conn.execute(text("ALTER TABLE users ADD COLUMN last_request TIMESTAMP DEFAULT NOW()"))
            print("✅ Added last_request column")
        except Exception as e:
            print(f"⚠️ last_request column: {e}")
        
        try:
            # Add request_count column
            conn.execute(text("ALTER TABLE users ADD COLUMN request_count INTEGER DEFAULT 0"))
            print("✅ Added request_count column")
        except Exception as e:
            print(f"⚠️ request_count column: {e}")
        
        conn.commit()
    
    print("\n✅ Database migration completed!")

if __name__ == '__main__':
    print("🔄 Migrating database for security features...\n")
    migrate_database()
