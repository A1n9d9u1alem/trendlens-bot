"""
Realtime Updates Service
Handles live sports scores and breaking news updates
"""

from database import SessionLocal, Content, User
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class RealtimeUpdates:
    """Realtime updates for sports and news"""
    
    def __init__(self, bot_instance: 'TrendLensBot') -> None:
        self.bot = bot_instance
        self.telegram_bot: Optional[Bot] = None
        self.running = False
        self.sports_task = None
        self.news_task = None
        
        # Update intervals (seconds)
        self.SPORTS_INTERVAL = 300  # 5 minutes
        self.NEWS_INTERVAL = 600    # 10 minutes
        
        # Keywords for breaking news
        self.BREAKING_NEWS_KEYWORDS = [
            'breaking', 'urgent', 'alert', 'just in', 'developing',
            'confirmed', 'official', 'exclusive', 'live', 'update'
        ]
        
        # Sports keywords for live events
        self.LIVE_SPORTS_KEYWORDS = [
            'goal', 'score', 'live', 'match', 'game', 'win', 'loss',
            'final', 'halftime', 'penalty', 'red card', 'injury'
        ]
    
    def set_telegram_bot(self, bot: Bot) -> None:
        """Set the Telegram bot instance"""
        self.telegram_bot = bot
    
    async def start_realtime_updates(self) -> None:
        """Start all realtime update tasks"""
        if self.running:
            logger.info("Realtime updates already running")
            return
        
        self.running = True
        logger.info("Starting realtime updates...")
        
        # Start sports updates
        self.sports_task = asyncio.create_task(self._sports_update_loop())
        
        # Start news updates
        self.news_task = asyncio.create_task(self._news_update_loop())
        
        logger.info("✅ Realtime updates started")
    
    async def stop_realtime_updates(self) -> None:
        """Stop all realtime update tasks"""
        self.running = False
        
        if self.sports_task:
            self.sports_task.cancel()
            try:
                await self.sports_task
            except asyncio.CancelledError:
                pass
        
        if self.news_task:
            self.news_task.cancel()
            try:
                await self.news_task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ Realtime updates stopped")
    
    async def _sports_update_loop(self) -> None:
        """Main loop for sports updates"""
        logger.info("Sports update loop started")
        
        while self.running:
            try:
                await self._check_sports_updates()
                await asyncio.sleep(self.SPORTS_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sports update loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _news_update_loop(self) -> None:
        """Main loop for news updates"""
        logger.info("News update loop started")
        
        while self.running:
            try:
                await self._check_news_updates()
                await asyncio.sleep(self.NEWS_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in news update loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _check_sports_updates(self) -> None:
        """Check for new sports updates"""
        db = SessionLocal()
        try:
            # Get recent sports content (last 10 minutes)
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
            
            sports_content = db.query(Content).filter(
                Content.category == 'sports',
                Content.created_at >= cutoff,
                Content.trend_score >= 60  # Only high-quality content
            ).order_by(Content.created_at.desc()).limit(5).all()
            
            for content in sports_content:
                # Check if it's live sports content
                if self._is_live_sports(content):
                    await self._notify_sports_update(content)
            
        except Exception as e:
            logger.error(f"Error checking sports updates: {e}")
        finally:
            db.close()
    
    async def _check_news_updates(self) -> None:
        """Check for breaking news"""
        db = SessionLocal()
        try:
            # Get recent news content (last 15 minutes)
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
            
            news_content = db.query(Content).filter(
                Content.category == 'news',
                Content.created_at >= cutoff,
                Content.trend_score >= 70  # Only high-quality breaking news
            ).order_by(Content.created_at.desc()).limit(5).all()
            
            for content in news_content:
                # Check if it's breaking news
                if self._is_breaking_news(content):
                    await self._notify_breaking_news(content)
            
        except Exception as e:
            logger.error(f"Error checking news updates: {e}")
        finally:
            db.close()
    
    def _is_live_sports(self, content: Content) -> bool:
        """Check if content is live sports event"""
        text = f"{content.title} {content.description or ''}".lower()
        
        # Check for live sports keywords
        matches = sum(1 for kw in self.LIVE_SPORTS_KEYWORDS if kw in text)
        
        return matches >= 2  # At least 2 keywords
    
    def _is_breaking_news(self, content: Content) -> bool:
        """Check if content is breaking news"""
        text = f"{content.title} {content.description or ''}".lower()
        
        # Check for breaking news keywords
        matches = sum(1 for kw in self.BREAKING_NEWS_KEYWORDS if kw in text)
        
        return matches >= 1  # At least 1 keyword
    
    async def _notify_sports_update(self, content: Content) -> None:
        """Send sports update notification to Pro users"""
        if not self.telegram_bot:
            return
        
        db = SessionLocal()
        try:
            # Get Pro users who want sports notifications
            pro_users = db.query(User).filter(
                User.is_premium == True
            ).all()
            
            if not pro_users:
                return
            
            # Build notification message
            message = (
                f"⚽ LIVE SPORTS UPDATE\n\n"
                f"📌 {content.title}\n\n"
                f"🔗 Platform: {content.platform}\n"
                f"🌐 {content.url}\n\n"
                f"⚡ Real-time update for Pro members"
            )
            
            # Send to Pro users (with rate limiting)
            sent = 0
            for user in pro_users[:50]:  # Limit to 50 users per update
                try:
                    await self.telegram_bot.send_message(
                        chat_id=user.telegram_id,
                        text=message
                    )
                    sent += 1
                    await asyncio.sleep(0.1)  # Rate limit: 10 messages/second
                except TelegramError as e:
                    logger.warning(f"Failed to send to user {user.telegram_id}: {e}")
                except Exception as e:
                    logger.error(f"Error sending notification: {e}")
            
            logger.info(f"Sent sports update to {sent} Pro users")
            
        except Exception as e:
            logger.error(f"Error notifying sports update: {e}")
        finally:
            db.close()
    
    async def _notify_breaking_news(self, content: Content) -> None:
        """Send breaking news notification to Pro users"""
        if not self.telegram_bot:
            return
        
        db = SessionLocal()
        try:
            # Get Pro users who want news notifications
            pro_users = db.query(User).filter(
                User.is_premium == True
            ).all()
            
            if not pro_users:
                return
            
            # Build notification message
            message = (
                f"🚨 BREAKING NEWS\n\n"
                f"📰 {content.title}\n\n"
                f"🔗 Platform: {content.platform}\n"
                f"🌐 {content.url}\n\n"
                f"⚡ Real-time update for Pro members"
            )
            
            # Send to Pro users (with rate limiting)
            sent = 0
            for user in pro_users[:50]:  # Limit to 50 users per update
                try:
                    await self.telegram_bot.send_message(
                        chat_id=user.telegram_id,
                        text=message
                    )
                    sent += 1
                    await asyncio.sleep(0.1)  # Rate limit: 10 messages/second
                except TelegramError as e:
                    logger.warning(f"Failed to send to user {user.telegram_id}: {e}")
                except Exception as e:
                    logger.error(f"Error sending notification: {e}")
            
            logger.info(f"Sent breaking news to {sent} Pro users")
            
        except Exception as e:
            logger.error(f"Error notifying breaking news: {e}")
        finally:
            db.close()
    
    async def get_live_sports_summary(self) -> str:
        """Get summary of current live sports events"""
        db = SessionLocal()
        try:
            # Get recent sports content
            cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
            
            sports_content = db.query(Content).filter(
                Content.category == 'sports',
                Content.created_at >= cutoff,
                Content.trend_score >= 60
            ).order_by(Content.trend_score.desc()).limit(10).all()
            
            if not sports_content:
                return "No live sports events at the moment."
            
            summary = "⚽ Live Sports Events:\n\n"
            for i, content in enumerate(sports_content, 1):
                summary += f"{i}. {content.title[:60]}...\n"
                summary += f"   🔗 {content.platform}\n\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting sports summary: {e}")
            return "Error loading sports events."
        finally:
            db.close()
    
    async def get_breaking_news_summary(self) -> str:
        """Get summary of breaking news"""
        db = SessionLocal()
        try:
            # Get recent breaking news
            cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
            
            news_content = db.query(Content).filter(
                Content.category == 'news',
                Content.created_at >= cutoff,
                Content.trend_score >= 70
            ).order_by(Content.trend_score.desc()).limit(10).all()
            
            if not news_content:
                return "No breaking news at the moment."
            
            summary = "🚨 Breaking News:\n\n"
            for i, content in enumerate(news_content, 1):
                summary += f"{i}. {content.title[:60]}...\n"
                summary += f"   🔗 {content.platform}\n\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting news summary: {e}")
            return "Error loading breaking news."
        finally:
            db.close()
    
    def get_status(self) -> Dict[str, Any]:
        """Get realtime updates status"""
        return {
            'running': self.running,
            'sports_active': self.sports_task is not None and not self.sports_task.done(),
            'news_active': self.news_task is not None and not self.news_task.done(),
            'sports_interval': self.SPORTS_INTERVAL,
            'news_interval': self.NEWS_INTERVAL
        }
