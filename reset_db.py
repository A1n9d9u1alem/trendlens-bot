#!/usr/bin/env python3
"""Drop and recreate all tables"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

engine = create_engine(os.getenv('DATABASE_URL'))

print("Dropping old tables...")
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS interactions CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS content CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
    conn.commit()

print("Creating new tables...")
from database import create_tables
create_tables()

print("✅ Database reset successfully!")
