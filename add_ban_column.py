import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def add_ban_column():
    engine = create_engine(os.getenv('DATABASE_URL'))
    
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='is_banned'
            """))
            
            if result.fetchone() is None:
                # Add is_banned column
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN is_banned BOOLEAN DEFAULT FALSE
                """))
                conn.commit()
                print("Added is_banned column to users table")
            else:
                print("is_banned column already exists")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    add_ban_column()
