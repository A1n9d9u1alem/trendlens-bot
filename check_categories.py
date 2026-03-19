#!/usr/bin/env python3

import os
from sqlalchemy import create_engine, text
from database import SessionLocal, Content
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

def check_content_categories():
    """Check and fix content categorization issues"""
    db = SessionLocal()
    
    try:
        print("🔍 Analyzing content categories...")
        
        # Get all content with their categories
        contents = db.query(Content).all()
        
        # Count by category
        category_counts = Counter([c.category for c in contents])
        platform_counts = Counter([c.platform for c in contents])
        
        print(f"\n📊 Total content items: {len(contents)}")
        print("\n📂 Content by category:")
        for category, count in category_counts.most_common():
            print(f"  {category}: {count}")
        
        print("\n🌐 Content by platform:")
        for platform, count in platform_counts.most_common():
            print(f"  {platform}: {count}")
        
        # Check for miscategorized content
        print("\n🔍 Checking for potential miscategorization...")
        
        # Define category keywords for validation
        category_keywords = {
            'memes': ['meme', 'funny', 'humor', 'joke', 'lol', 'dank'],
            'sports': ['football', 'basketball', 'soccer', 'nba', 'nfl', 'sport', 'game', 'match', 'player', 'team'],
            'tech': ['technology', 'software', 'ai', 'programming', 'computer', 'tech', 'digital', 'app'],
            'gaming': ['game', 'gaming', 'esports', 'nintendo', 'xbox', 'playstation', 'pc gaming'],
            'entertainment': ['movie', 'music', 'celebrity', 'tv', 'show', 'entertainment', 'actor', 'singer'],
            'news': ['news', 'breaking', 'politics', 'world', 'update', 'report']
        }
        
        mismatched = []
        
        for content in contents:
            title_lower = content.title.lower()
            desc_lower = (content.description or '').lower()
            text = f"{title_lower} {desc_lower}"
            
            # Check if content matches its assigned category
            assigned_keywords = category_keywords.get(content.category, [])
            matches_assigned = any(keyword in text for keyword in assigned_keywords)
            
            # Check if it better matches another category
            better_matches = []
            for cat, keywords in category_keywords.items():
                if cat != content.category:
                    if any(keyword in text for keyword in keywords):
                        better_matches.append(cat)
            
            if not matches_assigned and better_matches:
                mismatched.append({
                    'id': content.id,
                    'title': content.title[:50],
                    'current_category': content.category,
                    'suggested_categories': better_matches,
                    'platform': content.platform
                })
        
        if mismatched:
            print(f"\n⚠️  Found {len(mismatched)} potentially miscategorized items:")
            for item in mismatched[:10]:  # Show first 10
                print(f"  ID {item['id']}: '{item['title']}...'")
                print(f"    Current: {item['current_category']} → Suggested: {item['suggested_categories']}")
                print(f"    Platform: {item['platform']}")
                print()
        else:
            print("\n✅ No obvious miscategorization found!")
        
        # Check for empty categories
        valid_categories = ['memes', 'sports', 'tech', 'gaming', 'entertainment', 'news']
        empty_categories = [cat for cat in valid_categories if cat not in category_counts]
        
        if empty_categories:
            print(f"\n📭 Empty categories: {empty_categories}")
        
        return mismatched
        
    finally:
        db.close()

def fix_categorization():
    """Fix obvious categorization issues"""
    db = SessionLocal()
    
    try:
        print("\n🔧 Fixing categorization issues...")
        
        # Fix obvious mismatches based on platform and keywords
        fixes = [
            # Reddit memes subreddits should be in memes category
            ("UPDATE content SET category = 'memes' WHERE platform = 'reddit' AND (url LIKE '%/r/memes/%' OR url LIKE '%/r/dankmemes/%' OR url LIKE '%/r/funny/%')", "Reddit memes"),
            
            # Reddit sports subreddits
            ("UPDATE content SET category = 'sports' WHERE platform = 'reddit' AND (url LIKE '%/r/sports/%' OR url LIKE '%/r/soccer/%' OR url LIKE '%/r/nba/%' OR url LIKE '%/r/nfl/%' OR url LIKE '%/r/cricket/%')", "Reddit sports"),
            
            # Reddit tech subreddits
            ("UPDATE content SET category = 'tech' WHERE platform = 'reddit' AND (url LIKE '%/r/technology/%' OR url LIKE '%/r/programming/%' OR url LIKE '%/r/gadgets/%')", "Reddit tech"),
            
            # Reddit gaming subreddits
            ("UPDATE content SET category = 'gaming' WHERE platform = 'reddit' AND (url LIKE '%/r/gaming/%' OR url LIKE '%/r/pcgaming/%' OR url LIKE '%/r/nintendo/%')", "Reddit gaming"),
            
            # Reddit entertainment subreddits
            ("UPDATE content SET category = 'entertainment' WHERE platform = 'reddit' AND (url LIKE '%/r/movies/%' OR url LIKE '%/r/music/%' OR url LIKE '%/r/television/%')", "Reddit entertainment"),
            
            # Reddit news subreddits
            ("UPDATE content SET category = 'news' WHERE platform = 'reddit' AND (url LIKE '%/r/news/%' OR url LIKE '%/r/worldnews/%')", "Reddit news"),
            
            # News platform should be in news category
            ("UPDATE content SET category = 'news' WHERE platform = 'news'", "News platform"),
        ]
        
        total_fixed = 0
        for query, description in fixes:
            result = db.execute(text(query))
            fixed_count = result.rowcount
            total_fixed += fixed_count
            if fixed_count > 0:
                print(f"  ✅ {description}: {fixed_count} items fixed")
        
        db.commit()
        print(f"\n🎉 Total items recategorized: {total_fixed}")
        
    except Exception as e:
        print(f"❌ Error fixing categorization: {e}")
        db.rollback()
    finally:
        db.close()

def validate_categories():
    """Validate that all content has valid categories"""
    db = SessionLocal()
    
    try:
        valid_categories = ['memes', 'sports', 'tech', 'gaming', 'entertainment', 'news']
        
        # Check for invalid categories
        invalid_content = db.query(Content).filter(~Content.category.in_(valid_categories)).all()
        
        if invalid_content:
            print(f"\n⚠️  Found {len(invalid_content)} items with invalid categories:")
            for content in invalid_content[:5]:
                print(f"  ID {content.id}: '{content.title[:50]}...' - Category: '{content.category}'")
            
            # Fix by setting to 'entertainment' as default
            for content in invalid_content:
                content.category = 'entertainment'
            
            db.commit()
            print(f"✅ Fixed {len(invalid_content)} items with invalid categories")
        else:
            print("\n✅ All content has valid categories!")
            
    finally:
        db.close()

if __name__ == '__main__':
    print("TrendLens Content Category Checker")
    print("=" * 50)
    
    # Check current state
    mismatched = check_content_categories()
    
    # Validate categories
    validate_categories()
    
    # Fix categorization
    fix_categorization()
    
    # Check again after fixes
    print("\n" + "=" * 50)
    print("After fixes:")
    check_content_categories()