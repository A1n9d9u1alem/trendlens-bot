"""Quick database diagnostics"""
from database import SessionLocal, User, Content
from datetime import datetime, timedelta, timezone

db = SessionLocal()

print("=== DATABASE STATUS ===\n")

# Check users
total_users = db.query(User).count()
pro_users = db.query(User).filter(User.is_premium == True).count()
print(f"Users: {total_users} total, {pro_users} Pro")

# Check content
total_content = db.query(Content).count()
print(f"Total content: {total_content}")

# Check recent content
six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
recent = db.query(Content).filter(Content.created_at >= six_hours_ago).count()
print(f"Last 6 hours: {recent}")

# Check trending content
trending = db.query(Content).filter(Content.trend_score >= 50).count()
print(f"Trending (score >= 50): {trending}")

# Check recent + trending
recent_trending = db.query(Content).filter(
    Content.created_at >= six_hours_ago,
    Content.trend_score >= 50
).count()
print(f"Recent + Trending: {recent_trending}")

# Top scores
top = db.query(Content).order_by(Content.trend_score.desc()).limit(5).all()
print(f"\nTop 5 trend scores:")
for c in top:
    print(f"   {c.trend_score:.1f} - {c.title[:50]}...")

db.close()
