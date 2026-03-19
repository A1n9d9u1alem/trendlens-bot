#!/usr/bin/env python3

import os
from sqlalchemy import create_engine, text
from database import SessionLocal, Content
from dotenv import load_dotenv

load_dotenv()

def nuclear_fix_categories():
    """Nuclear fix - completely separate categories with zero mixing"""
    db = SessionLocal()
    
    try:
        print("NUCLEAR FIX: Completely separating categories...")
        
        # Step 1: Delete ALL content that doesn't match strict URL patterns
        strict_patterns = {
            'memes': ["url LIKE '%/r/memes/%'", "url LIKE '%/r/dankmemes/%'", "url LIKE '%/r/funny/%'"],
            'sports': ["url LIKE '%/r/sports/%'", "url LIKE '%/r/soccer/%'", "url LIKE '%/r/nba/%'", "url LIKE '%/r/nfl/%'", "url LIKE '%/r/cricket/%'"],
            'entertainment': ["url LIKE '%/r/music/%'", "url LIKE '%/r/movies/%'", "url LIKE '%/r/television/%'"],
            'gaming': ["url LIKE '%/r/gaming/%'", "url LIKE '%/r/pcgaming/%'", "url LIKE '%/r/nintendo/%'"],
            'tech': ["url LIKE '%/r/technology/%'", "url LIKE '%/r/programming/%'", "url LIKE '%/r/gadgets/%'"],
            'news': ["url LIKE '%/r/news/%'", "url LIKE '%/r/worldnews/%'", "platform = 'news'"]
        }
        
        total_deleted = 0
        
        for category, patterns in strict_patterns.items():
            # Keep only content that matches URL patterns for this category
            url_condition = " OR ".join(patterns)
            delete_query = f"DELETE FROM content WHERE category = '{category}' AND NOT ({url_condition})"
            
            result = db.execute(text(delete_query))
            deleted = result.rowcount
            total_deleted += deleted
            print(f"  {category}: Deleted {deleted} mismatched items")
        
        # Step 2: Force correct categorization based on URL
        fixes = [
            ("UPDATE content SET category = 'memes' WHERE url LIKE '%/r/memes/%'", "memes subreddit"),
            ("UPDATE content SET category = 'memes' WHERE url LIKE '%/r/dankmemes/%'", "dankmemes subreddit"),
            ("UPDATE content SET category = 'memes' WHERE url LIKE '%/r/funny/%'", "funny subreddit"),
            
            ("UPDATE content SET category = 'sports' WHERE url LIKE '%/r/sports/%'", "sports subreddit"),
            ("UPDATE content SET category = 'sports' WHERE url LIKE '%/r/soccer/%'", "soccer subreddit"),
            ("UPDATE content SET category = 'sports' WHERE url LIKE '%/r/nba/%'", "nba subreddit"),
            ("UPDATE content SET category = 'sports' WHERE url LIKE '%/r/nfl/%'", "nfl subreddit"),
            ("UPDATE content SET category = 'sports' WHERE url LIKE '%/r/cricket/%'", "cricket subreddit"),
            
            ("UPDATE content SET category = 'entertainment' WHERE url LIKE '%/r/music/%'", "music subreddit"),
            ("UPDATE content SET category = 'entertainment' WHERE url LIKE '%/r/movies/%'", "movies subreddit"),
            ("UPDATE content SET category = 'entertainment' WHERE url LIKE '%/r/television/%'", "tv subreddit"),
            
            ("UPDATE content SET category = 'gaming' WHERE url LIKE '%/r/gaming/%'", "gaming subreddit"),
            ("UPDATE content SET category = 'gaming' WHERE url LIKE '%/r/pcgaming/%'", "pcgaming subreddit"),
            ("UPDATE content SET category = 'gaming' WHERE url LIKE '%/r/nintendo/%'", "nintendo subreddit"),
            
            ("UPDATE content SET category = 'tech' WHERE url LIKE '%/r/technology/%'", "technology subreddit"),
            ("UPDATE content SET category = 'tech' WHERE url LIKE '%/r/programming/%'", "programming subreddit"),
            ("UPDATE content SET category = 'tech' WHERE url LIKE '%/r/gadgets/%'", "gadgets subreddit"),
            
            ("UPDATE content SET category = 'news' WHERE url LIKE '%/r/news/%'", "news subreddit"),
            ("UPDATE content SET category = 'news' WHERE url LIKE '%/r/worldnews/%'", "worldnews subreddit"),
            ("UPDATE content SET category = 'news' WHERE platform = 'news'", "news platform"),
        ]
        
        total_fixed = 0
        for query, desc in fixes:
            result = db.execute(text(query))
            fixed = result.rowcount
            total_fixed += fixed
            if fixed > 0:
                print(f"  Fixed {fixed} items for {desc}")
        
        db.commit()
        
        print(f"\nNUCLEAR FIX COMPLETE:")
        print(f"  Deleted: {total_deleted} mismatched items")
        print(f"  Fixed: {total_fixed} items")
        
        # Final counts
        print("\nFinal category counts:")
        categories = ['memes', 'sports', 'entertainment', 'gaming', 'tech', 'news']
        for cat in categories:
            count = db.execute(text(f"SELECT COUNT(*) FROM content WHERE category = '{cat}'")).scalar()
            print(f"  {cat}: {count}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    nuclear_fix_categories()