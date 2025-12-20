#!/usr/bin/env python3
"""
Create new tables for analytics and moderation
"""

from database import engine, Base, Analytics, ContentModeration

def migrate():
    """Create new tables"""
    print("Creating new tables...")
    
    try:
        # Create only new tables
        Analytics.__table__.create(engine, checkfirst=True)
        ContentModeration.__table__.create(engine, checkfirst=True)
        
        print("✅ Tables created successfully:")
        print("  - analytics")
        print("  - content_moderation")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == '__main__':
    migrate()
