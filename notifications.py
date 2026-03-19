"""
Trending Content Notifications
Sends alerts to Pro users about new viral content in their favorite categories
"""

import os
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Bot
from sqlalchemy import and_
from database import SessionLocal, User, Content, Analytics
from database import NotificationLog
from dotenv import load_dotenv

load_dotenv()

class NotificationService:
    def __init__(self):
        self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        self.db = SessionLocal()
        
    async def send_trending_alerts(self):
        """Send notifications about new trending content"""
        try:
            # Get Pro users with notifications enabled
            pro_users = self.db.query(User).filter(
                User.is_premium == True,
                User.notification_enabled == True
            ).all()
            
            if not pro_users:
                print("No Pro users with notifications enabled")
                return
            
            # Get content from last 6 hours with good trend score
            six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
            trending_content = self.db.query(Content).filter(
                Content.created_at >= six_hours_ago,
                Content.trend_score >= 50
            ).order_by(Content.trend_score.desc()).limit(50).all()
            
            if not trending_content:
                print(f"No trending content found (last 6h, score >= 50)")
                return
            
            print(f"Found {len(trending_content)} trending items")
            
            # Group content by category
            by_category = {}
            for content in trending_content:
                if content.category not in by_category:
                    by_category[content.category] = []
                by_category[content.category].append(content)
            
            # Send notifications to users
            sent_count = 0
            for user in pro_users:
                try:
                    # Check user's notification preferences
                    import json
                    user_categories = json.loads(user.notification_categories) if user.notification_categories else None
                    
                    # Get user's favorite category
                    favorite = self.db.query(Analytics.category).filter(
                        Analytics.user_id == user.id,
                        Analytics.category.isnot(None)
                    ).group_by(Analytics.category).order_by(
                        self.db.func.count(Analytics.category).desc()
                    ).first()
                    
                    category = None
                    if user_categories:
                        # Use user's preferred categories
                        for cat in user_categories:
                            if cat in by_category:
                                category = cat
                                break
                    elif favorite and favorite[0] in by_category:
                        category = favorite[0]
                    
                    if not category:
                        continue
                    
                    items = by_category[category][:3]
                    
                    message = f"🔥 NEW TRENDING in {category.upper()}!\n\n"
                    for i, item in enumerate(items, 1):
                        message += f"{i}. {item.title[:60]}...\n"
                        message += f"   📊 Score: {int(item.trend_score)}\n\n"
                    
                    message += f"View more: /start"
                    
                    # Send notification
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message
                    )
                    
                    # Log successful delivery
                    for item in items:
                        log = NotificationLog(
                            user_id=user.id,
                            content_id=item.id,
                            status='sent',
                            sent_at=datetime.now(timezone.utc)
                        )
                        self.db.add(log)
                    
                    sent_count += 1
                    print(f"✅ Sent notification to user {user.telegram_id}")
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    # Log failed delivery
                    log = NotificationLog(
                        user_id=user.id,
                        status='failed',
                        error_message=str(e),
                        created_at=datetime.now(timezone.utc)
                    )
                    self.db.add(log)
                    print(f"Failed to notify user {user.telegram_id}: {e}")
            
            self.db.commit()
            print(f"Sent {sent_count} notifications")
                    
        except Exception as e:
            print(f"Notification service error: {e}")
        finally:
            self.db.close()

async def main():
    """Run notification service"""
    service = NotificationService()
    await service.send_trending_alerts()

if __name__ == '__main__':
    asyncio.run(main())
