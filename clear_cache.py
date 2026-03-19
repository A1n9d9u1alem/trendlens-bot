#!/usr/bin/env python3

import os
import sys
import json
import ssl
import redis
from database import SessionLocal, Content
from dotenv import load_dotenv

load_dotenv()

def clear_redis_cache():
    """Clear Redis cache to force fresh categorized content"""
    
    try:
        redis_url = os.getenv('REDIS_URL')
        if redis_url.startswith('redis://') and 'upstash.io' in redis_url:
            redis_url = redis_url.replace('redis://', 'rediss://', 1)
        redis_client = redis.from_url(redis_url, decode_responses=False)
        
        print("Clearing Redis cache...")
        
        categories = ['memes', 'sports', 'tech', 'gaming', 'entertainment', 'news']
        
        for category in categories:
            cache_key = f"trending:{category}"
            
            try:
                # Clear the cache for this category
                deleted = redis_client.delete(cache_key)
                print(f"  Cleared cache for '{category}': {deleted} keys deleted")
                    
            except Exception as e:
                print(f"  Error clearing cache for {category}: {e}")
        
        print("Redis cache cleared! Bot will rebuild with proper categorization.")
        
    except Exception as e:
        print(f"Redis connection error: {e}")
        print("Cache will be rebuilt automatically when bot runs")

if __name__ == '__main__':
    print("TrendLens Redis Cache Cleaner")
    print("=" * 40)
    clear_redis_cache()