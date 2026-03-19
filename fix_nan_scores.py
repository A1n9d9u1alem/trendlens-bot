"""Fix NaN trend scores in database"""
from database import SessionLocal, Content
from sqlalchemy import text
import math

db = SessionLocal()

try:
    print("Fixing NaN trend scores...\n")
    
    # Find content with NaN scores
    result = db.execute(text("""
        SELECT id, engagement_score, created_at 
        FROM content 
        WHERE trend_score IS NULL 
        OR trend_score = 'NaN'::float 
        OR trend_score < 0
    """))
    
    rows = result.fetchall()
    print(f"Found {len(rows)} items with invalid scores\n")
    
    fixed = 0
    for row in rows:
        content_id, engagement, created_at = row
        
        # Recalculate score
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).timestamp()
            ts = created_at.timestamp() if created_at else now
            age = max(0, now - ts)
            freshness = max(0, 1 - (age / 86400))
            
            eng = float(engagement) if engagement else 0
            score = math.log(eng + 1) * freshness
            score = max(0, score) if not math.isnan(score) and math.isfinite(score) else 0
            
            db.execute(
                text("UPDATE content SET trend_score = :score WHERE id = :id"),
                {"score": score, "id": content_id}
            )
            fixed += 1
            
            if fixed % 100 == 0:
                print(f"Fixed {fixed} items...")
                db.commit()
                
        except Exception as e:
            print(f"Error fixing ID {content_id}: {e}")
            continue
    
    db.commit()
    print(f"\nFixed {fixed} items successfully!")
    
    # Verify
    result = db.execute(text("""
        SELECT COUNT(*) 
        FROM content 
        WHERE trend_score IS NULL 
        OR trend_score = 'NaN'::float 
        OR trend_score < 0
    """))
    remaining = result.fetchone()[0]
    print(f"Remaining invalid scores: {remaining}")
    
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
