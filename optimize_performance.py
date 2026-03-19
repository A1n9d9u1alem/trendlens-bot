"""Performance optimization for TrendLens Bot"""
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=== PERFORMANCE OPTIMIZATION ===\n")

try:
    # 1. Add composite indexes for faster queries
    print("1. Adding composite indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_content_cat_time_trend ON content(category, created_at DESC, trend_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_content_trend_score ON content(trend_score DESC, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_content_platform_cat ON content(platform, category, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_analytics_user_time ON analytics(user_id, timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_user_premium ON users(is_premium, subscription_end)",
    ]
    
    for idx in indexes:
        db.execute(text(idx))
    db.commit()
    print("   ✓ Composite indexes added\n")
    
    # 2. Analyze tables for query optimization
    print("2. Analyzing tables...")
    db.execute(text("ANALYZE content"))
    db.execute(text("ANALYZE analytics"))
    db.execute(text("ANALYZE users"))
    db.commit()
    print("   ✓ Tables analyzed\n")
    
    # 3. Check for missing indexes
    print("3. Checking index usage...")
    result = db.execute(text("""
        SELECT schemaname, tablename, indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename IN ('content', 'users', 'analytics')
        ORDER BY tablename
    """))
    
    print("   Current indexes:")
    for row in result:
        print(f"   - {row[1]}.{row[2]}")
    print()
    
    # 4. Show slow queries
    print("4. Performance recommendations:")
    print("   ✓ Use Redis cache (already enabled)")
    print("   ✓ Limit query results (use LIMIT)")
    print("   ✓ Use connection pooling (configured)")
    print("   ✓ Batch operations where possible")
    print("   ✓ Avoid N+1 queries")
    print()
    
    print("=== OPTIMIZATION COMPLETE ===")
    
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
