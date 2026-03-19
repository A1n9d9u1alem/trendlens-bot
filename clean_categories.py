#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text
from database import SessionLocal, Content
from dotenv import load_dotenv

load_dotenv()

def clean_categorization():
    """Clean up miscategorized content with strict rules"""
    db = SessionLocal()
    
    try:
        print("Cleaning content categorization...")
        
        # Define strict category rules
        category_rules = {
            'memes': {
                'subreddits': ['/r/memes/', '/r/dankmemes/', '/r/funny/', '/r/comedyheaven/'],
                'keywords': ['meme', 'funny', 'humor', 'joke', 'lol', 'comedy', 'hilarious']
            },
            'sports': {
                'subreddits': ['/r/sports/', '/r/soccer/', '/r/nba/', '/r/nfl/', '/r/cricket/', '/r/tennis/'],
                'keywords': ['football', 'basketball', 'sports', 'game', 'match', 'player', 'team']
            },
            'entertainment': {
                'subreddits': ['/r/music/', '/r/movies/', '/r/television/', '/r/dance/'],
                'keywords': ['music', 'dance', 'movie', 'celebrity', 'artist', 'singer']
            },
            'gaming': {
                'subreddits': ['/r/gaming/', '/r/pcgaming/', '/r/nintendo/', '/r/xbox/', '/r/playstation/'],
                'keywords': ['game', 'gaming', 'esports', 'steam', 'twitch']
            },
            'tech': {
                'subreddits': ['/r/technology/', '/r/programming/', '/r/gadgets/', '/r/apple/'],
                'keywords': ['tech', 'software', 'AI', 'programming', 'gadget']
            },
            'news': {
                'subreddits': ['/r/news/', '/r/worldnews/', '/r/politics/'],
                'keywords': ['news', 'breaking', 'politics', 'world']
            }
        }
        
        total_fixed = 0
        
        # Fix by subreddit URL
        for category, rules in category_rules.items():
            for subreddit in rules['subreddits']:
                query = f"UPDATE content SET category = '{category}' WHERE url LIKE '%{subreddit}%'"
                result = db.execute(text(query))
                fixed_count = result.rowcount
                total_fixed += fixed_count
                if fixed_count > 0:
                    print(f"  Fixed {fixed_count} items for {category} from {subreddit}")
        
        # Fix news platform content
        result = db.execute(text("UPDATE content SET category = 'news' WHERE platform = 'news'"))
        fixed_count = result.rowcount
        total_fixed += fixed_count
        if fixed_count > 0:
            print(f"  Fixed {fixed_count} news platform items")
        
        # Remove content that doesn't belong to any valid category
        valid_categories = list(category_rules.keys())
        placeholders = ','.join([f"'{cat}'" for cat in valid_categories])
        result = db.execute(text(f"DELETE FROM content WHERE category NOT IN ({placeholders})"))
        deleted_count = result.rowcount
        if deleted_count > 0:
            print(f"  Deleted {deleted_count} items with invalid categories")
        
        db.commit()
        print(f"\\nTotal items recategorized: {total_fixed}")
        print(f"Total items deleted: {deleted_count}")
        
        # Show final counts
        print("\\nFinal category distribution:")
        for category in valid_categories:
            count = db.execute(text(f"SELECT COUNT(*) FROM content WHERE category = '{category}'")).scalar()
            print(f"  {category}: {count}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    print("TrendLens Content Categorization Cleaner")
    print("=" * 50)
    clean_categorization()