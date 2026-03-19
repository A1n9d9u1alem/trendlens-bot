#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import ssl
import redis
from database import SessionLocal, Content
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

load_dotenv()

def check_redis_cache():
    """Check and fix Redis cache categorization"""
    
    try:
        redis_url = os.getenv('REDIS_URL')
        if redis_url.startswith('redis://') and 'upstash.io' in redis_url:
            redis_url = redis_url.replace('redis://', 'rediss://', 1)
        redis_client = redis.from_url(redis_url, decode_responses=False)
        
        print("Checking Redis cache categorization...")
        
        categories = ['memes', 'sports', 'tech', 'gaming', 'entertainment', 'news']
        
        for category in categories:
            cache_key = f"trending:{category}"
            
            # Get cached items
            try:
                cached_items = redis_client.zrevrange(cache_key, 0, -1)
                print(f"\nCategory '{category}': {len(cached_items)} cached items")
                
                # Check if cached items match the category
                mismatched = 0
                for item_bytes in cached_items:
                    try:
                        item = json.loads(item_bytes.decode('utf-8'))
                        if item.get('category') != category:
                            mismatched += 1
                    except:
                        mismatched += 1
                
                if mismatched > 0:
                    print(f"  WARNING: {mismatched} items don't match category")
                    # Clear the cache for this category
                    redis_client.delete(cache_key)
                    print(f"  Cleared cache for category '{category}'")
                else:
                    print(f"  All items properly categorized")
                    
            except Exception as e:
                print(f"  Error checking cache for {category}: {e}")
        
        print("\nRedis cache check completed!")
        
    except Exception as e:
        print(f"Redis connection error: {e}")
        print("Cache will be rebuilt automatically when bot runs")

def rebuild_cache():
    """Rebuild Redis cache with properly categorized content"""
    
    try:
        redis_url = os.getenv('REDIS_URL')
        if redis_url.startswith('redis://') and 'upstash.io' in redis_url:
            redis_url = redis_url.replace('redis://', 'rediss://', 1)
        redis_client = redis.from_url(redis_url, decode_responses=False)
        
        # Connect to database
        db = SessionLocal()
        
        print("Rebuilding Redis cache with proper categorization...")
        
        categories = ['memes', 'sports', 'tech', 'gaming', 'entertainment', 'news']
        
        for category in categories:
            cache_key = f"trending:{category}"
            
            # Clear existing cache
            redis_client.delete(cache_key)
            
            # Get top content from database for this category
            contents = db.query(Content).filter(
                Content.category == category
            ).order_by(Content.trend_score.desc()).limit(20).all()
            
            # Add to cache
            for content in contents:
                try:
                    trend_score = float(content.trend_score) if content.trend_score is not None else 0.0
                    engagement_score = float(content.engagement_score) if content.engagement_score is not None else 0.0
                    
                    content_dict = {
                        'id': content.id,
                        'title': content.title,
                        'url': content.url,
                        'platform': content.platform,
                        'category': content.category,
                        'thumbnail': content.thumbnail,
                        'description': content.description,
                        'engagement_score': engagement_score,
                        'trend_score': trend_score
                    }
                    
                    redis_client.zadd(cache_key, {
                        json.dumps(content_dict): trend_score
                    })
                except Exception as e:
                    print(f"    Error caching item {content.id}: {e}")
                    continue
            
            # Set expiration (30 minutes)
            redis_client.expire(cache_key, 1800)
            
            print(f"  Cached {len(contents)} items for category '{category}'")
        
        db.close()
        print("Cache rebuild completed!")
        
    except Exception as e:
        print(f"Error rebuilding cache: {e}")

if __name__ == '__main__':
    print("TrendLens Redis Cache Checker")
    print("=" * 40)
    
    # Check current cache
    check_redis_cache()
    
    # Rebuild cache
    print("\n" + "=" * 40)
    rebuild_cache()