import os
import redis
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv('REDIS_URL')
print(f"Testing Redis connection...")
print(f"URL: {redis_url[:30]}...")

try:
    if redis_url.startswith('redis://'):
        redis_url = redis_url.replace('redis://', 'rediss://', 1)
        print("Converted to SSL: rediss://")
    
    r = redis.from_url(redis_url, decode_responses=True)
    r.ping()
    print("Redis PING successful")
    
    r.set('test_key', 'test_value')
    print("Redis SET successful")
    
    val = r.get('test_key')
    print(f"Redis GET successful: {val}")
    
    r.delete('test_key')
    print("Redis DELETE successful")
    
    print("\nRedis connection is working perfectly!")
    print("Caching is ENABLED")
    
except Exception as e:
    print(f"Redis error: {e}")
    print("Caching is DISABLED")
