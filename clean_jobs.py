"""Clean non-freelance jobs from jobs category"""
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    print("Cleaning non-freelance jobs...")
    
    # Delete jobs that don't contain freelance keywords
    result = db.execute(text("""
        DELETE FROM content 
        WHERE category = 'jobs'
        AND LOWER(title) NOT SIMILAR TO '%(freelance|remote|upwork|fiverr|contract|gig|work from home|freelancer)%'
    """))
    
    deleted = result.rowcount
    db.commit()
    
    print(f"Deleted {deleted} non-freelance job posts")
    
    # Show remaining jobs count
    result = db.execute(text("SELECT COUNT(*) FROM content WHERE category = 'jobs'"))
    remaining = result.fetchone()[0]
    print(f"Remaining freelance jobs: {remaining}")
    
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
