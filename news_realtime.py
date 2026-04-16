"""
Real-time News Updates System
Delivers breaking news within seconds
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging
import hashlib

class NewsRealtimeUpdater:
    def __init__(self, bot_application):
        self.app = bot_application
        self.last_news_check = {}  # Track last check per source
        self.seen_news = set()  # Track seen news to avoid duplicates
        
        # News sources and categories
        self.news_categories = {
            'breaking': {'priority': 1, 'keywords': ['breaking', 'just in', 'urgent', 'developing']},
            'world': {'priority': 2, 'keywords': ['world', 'international', 'global']},
            'politics': {'priority': 2, 'keywords': ['politics', 'government', 'election']},
            'business': {'priority': 3, 'keywords': ['business', 'economy', 'market', 'stock']},
            'technology': {'priority': 3, 'keywords': ['tech', 'technology', 'ai', 'innovation']},
            'sports_news': {'priority': 3, 'keywords': ['sports', 'game', 'match', 'player']}
        }
        
        # Breaking news keywords for instant alerts
        self.breaking_keywords = [
            'breaking', 'just in', 'urgent', 'alert', 'developing',
            'live', 'happening now', 'confirmed', 'official',
            'major', 'significant', 'critical', 'emergency'
        ]
        
        # News APIs (configure these)
        self.news_apis = {
            'newsapi': 'https://newsapi.org/v2/top-headlines',
            'guardian': 'https://content.guardianapis.com/search',
            'nyt': 'https://api.nytimes.com/svc/topstories/v2/home.json'
        }
        
    async def start_realtime_news_updates(self):
        """Start background task for real-time news updates"""
        while True:
            try:
                await self.check_breaking_news()
                await asyncio.sleep(30)  # Check every 30 seconds for breaking news
            except Exception as e:
                logging.error(f"News update error: {e}")
                await asyncio.sleep(60)
    
    async def check_breaking_news(self):
        """Check for breaking news and send instant alerts"""
        try:
            # Fetch latest news from multiple sources
            news_items = await self.fetch_latest_news()
            
            for news in news_items:
                news_hash = self.generate_news_hash(news)
                
                # Skip if already seen
                if news_hash in self.seen_news:
                    continue
                
                # Check if breaking news
                if self.is_breaking_news(news):
                    await self.send_breaking_news_alert(news)
                    self.seen_news.add(news_hash)
                    
                    # Clean old seen news (keep last 1000)
                    if len(self.seen_news) > 1000:
                        self.seen_news = set(list(self.seen_news)[-500:])
                        
        except Exception as e:
            logging.error(f"Error checking breaking news: {e}")
    
    def generate_news_hash(self, news: Dict) -> str:
        """Generate unique hash for news item"""
        title = news.get('title', '')
        source = news.get('source', '')
        content = f"{title}{source}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_breaking_news(self, news: Dict) -> bool:
        """Check if news is breaking/urgent"""
        title = news.get('title', '').lower()
        description = news.get('description', '').lower()
        text = f"{title} {description}"
        
        # Check for breaking keywords
        return any(keyword in text for keyword in self.breaking_keywords)
    
    async def fetch_latest_news(self) -> List[Dict]:
        """Fetch latest news from APIs"""
        # Placeholder - implement with actual news APIs
        # For now, return empty list
        return []
    
    async def send_breaking_news_alert(self, news: Dict):
        """Send breaking news alert to subscribed users"""
        from database import SessionLocal, User
        
        title = news.get('title', '')
        url = news.get('url', '')
        source = news.get('source', '')
        published = news.get('published_at', '')
        
        # Format message
        message = (
            f"🚨 BREAKING NEWS\n\n"
            f"📰 {title}\n\n"
            f"📍 Source: {source}\n"
            f"🕒 {published}\n\n"
            f"🔗 {url}"
        )
        
        # Send to Pro users subscribed to news
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                User.is_premium == True
            ).all()
            
            for user in users:
                try:
                    await self.app.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message
                    )
                    await asyncio.sleep(0.05)  # Rate limiting
                except Exception as e:
                    logging.error(f"Failed to send news to {user.telegram_id}: {e}")
                    
        finally:
            db.close()
    
    def categorize_news(self, news: Dict) -> str:
        """Categorize news based on content"""
        title = news.get('title', '').lower()
        description = news.get('description', '').lower()
        text = f"{title} {description}"
        
        # Check each category
        for category, info in self.news_categories.items():
            keywords = info['keywords']
            if any(keyword in text for keyword in keywords):
                return category
        
        return 'general'
    
    async def get_trending_news(self, category: str = None, hours: int = 24) -> List[Dict]:
        """Get trending news for specific category"""
        # Placeholder for trending news
        return []
    
    async def search_news(self, query: str, limit: int = 10) -> List[Dict]:
        """Search news by keywords"""
        # Placeholder for news search
        return []


# Global instance
news_updater = None

def init_news_updater(bot_application):
    """Initialize news updater"""
    global news_updater
    news_updater = NewsRealtimeUpdater(bot_application)
    return news_updater

def get_news_updater():
    """Get news updater instance"""
    return news_updater
