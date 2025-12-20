#!/usr/bin/env python3
"""
Analytics Report Generator for TrendLens Bot
"""

from database import SessionLocal, User, Analytics, Content
from datetime import datetime, timedelta, timezone
from collections import Counter
import json

def generate_report(days=7):
    """Generate analytics report"""
    db = SessionLocal()
    
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        # User metrics
        total_users = db.query(User).count()
        active_users = db.query(Analytics).filter(
            Analytics.timestamp >= cutoff
        ).distinct(Analytics.user_id).count()
        
        # Event metrics
        events = db.query(Analytics).filter(
            Analytics.timestamp >= cutoff
        ).all()
        
        event_counts = Counter([e.event_type for e in events])
        category_views = Counter([e.category for e in events if e.category])
        
        # Top content
        top_content = db.query(Content).order_by(
            Content.engagement_score.desc()
        ).limit(10).all()
        
        print(f"\n📊 TrendLens Analytics Report (Last {days} days)")
        print("=" * 50)
        print(f"\n👥 Users:")
        print(f"  Total: {total_users}")
        print(f"  Active: {active_users}")
        print(f"  Engagement Rate: {(active_users/total_users*100):.1f}%")
        
        print(f"\n📈 Events:")
        for event, count in event_counts.most_common():
            print(f"  {event}: {count}")
        
        print(f"\n📁 Popular Categories:")
        for category, count in category_views.most_common():
            print(f"  {category}: {count} views")
        
        print(f"\n🔥 Top Content:")
        for i, content in enumerate(top_content, 1):
            print(f"  {i}. {content.title[:50]}... ({content.platform})")
        
        print("\n" + "=" * 50)
        
    finally:
        db.close()

if __name__ == '__main__':
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    generate_report(days)
