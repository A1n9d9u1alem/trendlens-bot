#!/usr/bin/env python3

import os
from sqlalchemy import create_engine, text
from database import SessionLocal, Content
from dotenv import load_dotenv

load_dotenv()

def eliminate_content_mixing():
    """Final fix - eliminate all content mixing by URL uniqueness"""
    db = SessionLocal()
    
    try:
        print("FINAL FIX: Eliminating content mixing...")
        
        # Step 1: Find duplicate URLs across categories
        duplicate_query = """
        SELECT url, COUNT(*) as count, array_agg(DISTINCT category) as categories
        FROM content 
        GROUP BY url 
        HAVING COUNT(*) > 1
        """
        
        result = db.execute(text(duplicate_query))
        duplicates = result.fetchall()
        
        print(f"Found {len(duplicates)} URLs appearing in multiple categories")
        
        # Step 2: For each duplicate, keep only in the most appropriate category
        category_priority = {
            'memes': ['/r/memes/', '/r/dankmemes/', '/r/funny/'],
            'sports': ['/r/sports/', '/r/soccer/', '/r/nba/', '/r/nfl/', '/r/cricket/'],
            'entertainment': ['/r/music/', '/r/movies/', '/r/television/'],
            'gaming': ['/r/gaming/', '/r/pcgaming/', '/r/nintendo/'],
            'tech': ['/r/technology/', '/r/programming/', '/r/gadgets/'],
            'news': ['/r/news/', '/r/worldnews/', 'newsapi.org']
        }
        
        fixed_count = 0
        for row in duplicates:
            url = row[0]
            categories = row[2]
            
            # Determine correct category based on URL
            correct_category = None
            for cat, patterns in category_priority.items():
                if any(pattern in url for pattern in patterns):
                    correct_category = cat
                    break
            
            if correct_category:
                # Delete from all other categories
                delete_query = "DELETE FROM content WHERE url = :url AND category != :correct_cat"
                db.execute(text(delete_query), {"url": url, "correct_cat": correct_category})
                fixed_count += 1
            else:
                # If no clear category, delete all but keep the first one found
                keep_category = categories[0]
                delete_query = "DELETE FROM content WHERE url = :url AND category != :keep_cat"
                db.execute(text(delete_query), {"url": url, "keep_cat": keep_category})
                fixed_count += 1
        
        # Step 3: Add unique constraint on URL to prevent future duplicates
        try:
            db.execute(text("ALTER TABLE content ADD CONSTRAINT unique_url UNIQUE (url)"))
            print("Added unique constraint on URL")
        except:
            print("Unique constraint already exists or failed to add")
        
        db.commit()
        
        print(f"Fixed {fixed_count} duplicate URLs")
        
        # Final verification
        print("\nFinal category distribution:")
        categories = ['memes', 'sports', 'entertainment', 'gaming', 'tech', 'news']
        for cat in categories:
            count = db.execute(text(f"SELECT COUNT(*) FROM content WHERE category = '{cat}'")).scalar()
            print(f"  {cat}: {count}")
        
        # Check for any remaining duplicates
        remaining = db.execute(text("SELECT COUNT(*) FROM (SELECT url FROM content GROUP BY url HAVING COUNT(*) > 1) as dups")).scalar()
        print(f"\nRemaining duplicates: {remaining}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    eliminate_content_mixing()