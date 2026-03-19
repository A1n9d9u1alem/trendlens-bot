"""Add database indexes for performance optimization"""
from database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()

indexes = [
    # Content table indexes
    "CREATE INDEX IF NOT EXISTS idx_content_category_date ON content(category, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_content_trend_score ON content(trend_score DESC)",
    "CREATE INDEX IF NOT EXISTS idx_content_created_at ON content(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_content_platform ON content(platform)",
    
    # Analytics table indexes
    "CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp DESC)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON analytics(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_category ON analytics(category)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_user_category ON analytics(user_id, category)",
    
    # User table indexes
    "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
    "CREATE INDEX IF NOT EXISTS idx_users_premium ON users(is_premium)",
    "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC)",
    
    # Payment table indexes
    "CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)",
    "CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at DESC)",
    
    # Interactions table indexes
    "CREATE INDEX IF NOT EXISTS idx_interactions_user_id ON interactions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_interactions_content_id ON interactions(content_id)",
    "CREATE INDEX IF NOT EXISTS idx_interactions_action ON interactions(action)",
]

try:
    print("Adding database indexes...")
    for idx, sql in enumerate(indexes, 1):
        try:
            db.execute(text(sql))
            db.commit()
            print(f"[{idx}/{len(indexes)}] Created: {sql.split('idx_')[1].split(' ON')[0]}")
        except Exception as e:
            print(f"[{idx}/{len(indexes)}] Skipped (already exists or error): {str(e)[:50]}")
            db.rollback()
    
    print("\nIndexes added successfully!")
    print("\nVerifying indexes...")
    
    # Verify indexes
    result = db.execute(text("""
        SELECT tablename, indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND indexname LIKE 'idx_%'
        ORDER BY tablename, indexname
    """))
    
    print("\nCurrent indexes:")
    for row in result:
        print(f"  {row[0]}.{row[1]}")
        
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()

print("\nDone! Bot queries should now be much faster.")
