import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def check_banned_users():
    engine = create_engine(os.getenv('DATABASE_URL'))
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT telegram_id, username, is_banned 
            FROM users 
            WHERE is_banned = TRUE
        """))
        
        banned = result.fetchall()
        
        if banned:
            print(f"Banned users ({len(banned)}):")
            for user in banned:
                print(f"  - ID: {user[0]}, Username: {user[1]}, Banned: {user[2]}")
        else:
            print("No banned users found")

if __name__ == '__main__':
    check_banned_users()
