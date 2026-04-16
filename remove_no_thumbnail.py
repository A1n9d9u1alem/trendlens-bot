"""
Remove Content Without Thumbnails
Cleans up database by removing content that has no thumbnail
"""

from database import SessionLocal, Content
from datetime import datetime, timezone
import time

def get_db_connection(max_retries=3):
    """Get database connection with retry logic"""
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Test connection
            db.execute('SELECT 1')
            return db
        except Exception as e:
            print(f"⚠️  Connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in 2 seconds...")
                time.sleep(2)
            else:
                raise Exception("❌ Could not connect to database after multiple attempts")
    return None

def remove_content_without_thumbnails():
    """Remove all content that doesn't have a thumbnail"""
    print("🔌 Connecting to database...")
    try:
        db = get_db_connection()
    except Exception as e:
        print(f"❌ {e}")
        print("\n💡 Tips:")
        print("  1. Check your internet connection")
        print("  2. Verify DATABASE_URL in .env file")
        print("  3. Check if database is accessible")
        print("  4. Try using direct connection instead of pooler")
        return
    
    try:
        print("✅ Connected to database!\n")
        
        # Count total content
        total_content = db.query(Content).count()
        print(f"📊 Total content in database: {total_content}")
        
        # Find content without thumbnails
        no_thumbnail = db.query(Content).filter(
            (Content.thumbnail == None) | (Content.thumbnail == '')
        ).all()
        
        print(f"🔍 Found {len(no_thumbnail)} items without thumbnails")
        
        if len(no_thumbnail) == 0:
            print("✅ All content has thumbnails!")
            return
        
        # Show some examples
        print("\n📋 Examples of content without thumbnails:")
        for i, content in enumerate(no_thumbnail[:5], 1):
            print(f"{i}. {content.title[:60]}... ({content.platform})")
        
        # Ask for confirmation
        print(f"\n⚠️  This will DELETE {len(no_thumbnail)} items from the database!")
        confirm = input("Type 'yes' to confirm deletion: ")
        
        if confirm.lower() != 'yes':
            print("❌ Deletion cancelled")
            return
        
        # Delete content without thumbnails in batches
        print("\n🗑️ Deleting content...")
        deleted_count = 0
        batch_size = 100
        
        for i in range(0, len(no_thumbnail), batch_size):
            batch = no_thumbnail[i:i+batch_size]
            for content in batch:
                try:
                    db.delete(content)
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️  Error deleting content {content.id}: {e}")
            
            db.commit()
            print(f"⏳ Progress: {deleted_count}/{len(no_thumbnail)}")
        
        # Show results
        remaining = db.query(Content).count()
        print(f"\n✅ Deletion complete!")
        print(f"🗑️  Deleted: {deleted_count} items")
        print(f"📊 Remaining: {remaining} items")
        print(f"📈 Removed: {(deleted_count/total_content*100):.1f}% of total content")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

def remove_content_without_thumbnails_by_category(category):
    """Remove content without thumbnails for a specific category"""
    db = SessionLocal()
    try:
        # Find content without thumbnails in category
        no_thumbnail = db.query(Content).filter(
            Content.category == category,
            (Content.thumbnail == None) | (Content.thumbnail == '')
        ).all()
        
        print(f"🔍 Found {len(no_thumbnail)} items without thumbnails in '{category}'")
        
        if len(no_thumbnail) == 0:
            print(f"✅ All content in '{category}' has thumbnails!")
            return
        
        # Ask for confirmation
        confirm = input(f"Delete {len(no_thumbnail)} items from '{category}'? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("❌ Deletion cancelled")
            return
        
        # Delete
        for content in no_thumbnail:
            db.delete(content)
        
        db.commit()
        print(f"✅ Deleted {len(no_thumbnail)} items from '{category}'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

def show_thumbnail_stats():
    """Show statistics about thumbnails"""
    print("🔌 Connecting to database...")
    try:
        db = get_db_connection()
    except Exception as e:
        print(f"❌ {e}")
        return
    
    try:
        print("✅ Connected!\n")
        
        total = db.query(Content).count()
        with_thumbnail = db.query(Content).filter(
            Content.thumbnail != None,
            Content.thumbnail != ''
        ).count()
        without_thumbnail = total - with_thumbnail
        
        print("\n📊 Thumbnail Statistics")
        print("=" * 50)
        print(f"Total Content: {total}")
        print(f"With Thumbnails: {with_thumbnail} ({with_thumbnail/total*100:.1f}%)")
        print(f"Without Thumbnails: {without_thumbnail} ({without_thumbnail/total*100:.1f}%)")
        print("=" * 50)
        
        # By category
        print("\n📂 By Category:")
        categories = ['memes', 'sports', 'entertainment', 'gaming', 'tech', 'news', 'jobs']
        for cat in categories:
            total_cat = db.query(Content).filter(Content.category == cat).count()
            with_thumb = db.query(Content).filter(
                Content.category == cat,
                Content.thumbnail != None,
                Content.thumbnail != ''
            ).count()
            without_thumb = total_cat - with_thumb
            
            if total_cat > 0:
                print(f"  {cat.title()}: {with_thumb}/{total_cat} ({with_thumb/total_cat*100:.0f}% with thumbnails)")
        
        # By platform
        print("\n🌐 By Platform:")
        from sqlalchemy import func
        platforms = db.query(Content.platform, func.count(Content.id)).group_by(Content.platform).all()
        for platform, count in platforms:
            with_thumb = db.query(Content).filter(
                Content.platform == platform,
                Content.thumbnail != None,
                Content.thumbnail != ''
            ).count()
            print(f"  {platform.title()}: {with_thumb}/{count} ({with_thumb/count*100:.0f}% with thumbnails)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

def fix_thumbnails_with_handler():
    """Try to fix missing thumbnails using ThumbnailHandler"""
    from thumbnail_handler import ThumbnailHandler
    
    db = SessionLocal()
    handler = ThumbnailHandler()
    
    try:
        # Find content without thumbnails
        no_thumbnail = db.query(Content).filter(
            (Content.thumbnail == None) | (Content.thumbnail == '')
        ).limit(100).all()  # Process in batches
        
        print(f"🔧 Attempting to fix {len(no_thumbnail)} items...")
        
        fixed = 0
        failed = 0
        
        for content in no_thumbnail:
            try:
                # Try to get thumbnail
                thumbnail = handler.get_thumbnail(content.url, content.platform)
                
                if thumbnail:
                    content.thumbnail = thumbnail
                    fixed += 1
                    print(f"✅ Fixed: {content.title[:50]}...")
                else:
                    failed += 1
                    print(f"❌ Failed: {content.title[:50]}...")
            except Exception as e:
                failed += 1
                print(f"⚠️  Error: {content.title[:50]}... - {e}")
        
        db.commit()
        
        print(f"\n📊 Results:")
        print(f"✅ Fixed: {fixed}")
        print(f"❌ Failed: {failed}")
        
    finally:
        db.close()

if __name__ == '__main__':
    import sys
    
    print("🖼️  Content Thumbnail Manager")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'stats':
            show_thumbnail_stats()
        elif command == 'fix':
            fix_thumbnails_with_handler()
        elif command == 'remove':
            if len(sys.argv) > 2:
                category = sys.argv[2]
                remove_content_without_thumbnails_by_category(category)
            else:
                remove_content_without_thumbnails()
        else:
            print("❌ Unknown command")
            print("\nUsage:")
            print("  python remove_no_thumbnail.py stats    - Show thumbnail statistics")
            print("  python remove_no_thumbnail.py fix      - Try to fix missing thumbnails")
            print("  python remove_no_thumbnail.py remove   - Remove all content without thumbnails")
            print("  python remove_no_thumbnail.py remove <category> - Remove by category")
    else:
        print("\n📋 Available Commands:")
        print("1. Show statistics")
        print("2. Try to fix missing thumbnails")
        print("3. Remove content without thumbnails")
        print("4. Remove by category")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ")
        
        if choice == '1':
            show_thumbnail_stats()
        elif choice == '2':
            fix_thumbnails_with_handler()
        elif choice == '3':
            remove_content_without_thumbnails()
        elif choice == '4':
            category = input("Enter category (memes/sports/tech/etc): ")
            remove_content_without_thumbnails_by_category(category)
        elif choice == '5':
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice")
