import requests
from database import SessionLocal, Content
from datetime import datetime, timezone

# Trigger aggregator
try:
    response = requests.get('http://localhost:3000/fetch/memes', timeout=30)
    print(f"Aggregator response: {response.json()}")
except Exception as e:
    print(f"Aggregator error: {e}")

# Check database
db = SessionLocal()
count = db.query(Content).filter(Content.category == 'memes').count()
print(f"Total memes in DB: {count}")
db.close()
