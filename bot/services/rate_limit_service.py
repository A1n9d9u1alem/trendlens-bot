"""
Rate Limiting Service
Handles daily content view limits for users
"""

from database import SessionLocal, User, UserInteraction
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class RateLimitService:
    """Service to handle rate limiting for users"""
    
    # Rate limits
    FREE_DAILY_LIMIT = 20  # Free users: 20 views per day
    PRO_DAILY_LIMIT = None  # Pro users: Unlimited
    
    @staticmethod
    def check_rate_limit(user_id: int) -> Tuple[bool, int, int]:
        """
        Check if user has exceeded daily rate limit
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Tuple of (allowed: bool, used: int, limit: int)
            - allowed: True if user can view more content
            - used: Number of views used today
            - limit: Daily limit for this user (0 = unlimited)
        """
        db = SessionLocal()
        try:
            # Get user
            db_user = db.query(User).filter(User.telegram_id == user_id).first()
            
            if not db_user:
                # User not found, allow (will be created on first interaction)
                return (True, 0, RateLimitService.FREE_DAILY_LIMIT)
            
            # Pro users have unlimited access
            if db_user.is_premium:
                return (True, 0, 0)  # 0 = unlimited
            
            # Get today's start time (midnight UTC)
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            
            # Count views today
            views_today = db.query(UserInteraction).filter(
                UserInteraction.user_id == db_user.id,
                UserInteraction.action == 'view',
                UserInteraction.timestamp >= today_start
            ).count()
            
            # Check if limit exceeded
            allowed = views_today < RateLimitService.FREE_DAILY_LIMIT
            
            return (allowed, views_today, RateLimitService.FREE_DAILY_LIMIT)
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # On error, allow access (fail open)
            return (True, 0, RateLimitService.FREE_DAILY_LIMIT)
        finally:
            db.close()
    
    @staticmethod
    def track_view(user_id: int, content_id: int) -> bool:
        """
        Track a content view for rate limiting
        
        Args:
            user_id: User's database ID (not telegram_id)
            content_id: Content ID being viewed
            
        Returns:
            True if tracked successfully
        """
        db = SessionLocal()
        try:
            # Create interaction record
            interaction = UserInteraction(
                user_id=user_id,
                content_id=content_id,
                action='view',
                timestamp=datetime.now(timezone.utc)
            )
            db.add(interaction)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error tracking view: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def get_reset_time() -> datetime:
        """
        Get the time when rate limit resets (next midnight UTC)
        
        Returns:
            Datetime of next reset
        """
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(days=1)
        reset_time = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        return reset_time
    
    @staticmethod
    def get_time_until_reset() -> str:
        """
        Get human-readable time until rate limit resets
        
        Returns:
            String like "5 hours 30 minutes"
        """
        reset_time = RateLimitService.get_reset_time()
        now = datetime.now(timezone.utc)
        time_diff = reset_time - now
        
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
        else:
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
    
    @staticmethod
    def format_limit_message(used: int, limit: int, is_premium: bool = False) -> str:
        """
        Format a user-friendly rate limit message
        
        Args:
            used: Number of views used
            limit: Daily limit
            is_premium: Whether user is premium
            
        Returns:
            Formatted message string
        """
        if is_premium:
            return "✨ Pro Member: Unlimited views"
        
        remaining = limit - used
        percentage = (used / limit) * 100
        
        # Progress bar
        filled = int(percentage / 10)
        bar = "█" * filled + "░" * (10 - filled)
        
        message = (
            f"📊 Daily Limit: {used}/{limit} views used\n"
            f"[{bar}] {percentage:.0f}%\n"
            f"⏳ Remaining: {remaining} views\n"
        )
        
        if remaining <= 5:
            message += f"\n⚠️ Running low! Resets in {RateLimitService.get_time_until_reset()}"
        
        if used >= limit:
            message += (
                f"\n\n❌ Daily limit reached!\n"
                f"⏰ Resets in {RateLimitService.get_time_until_reset()}\n\n"
                f"💡 Upgrade to Pro for unlimited access:\n"
                f"/subscribe"
            )
        
        return message
    
    @staticmethod
    def get_limit_exceeded_message() -> str:
        """
        Get message to show when rate limit is exceeded
        
        Returns:
            Formatted error message
        """
        reset_time = RateLimitService.get_time_until_reset()
        
        return (
            f"⚠️ Daily Limit Reached!\n\n"
            f"🆓 Free Tier: {RateLimitService.FREE_DAILY_LIMIT} views per day\n"
            f"📊 You've used all your daily views\n\n"
            f"⏰ Limit resets in: {reset_time}\n\n"
            f"✨ Want unlimited access?\n\n"
            f"🎯 Pro Benefits:\n"
            f"• Unlimited content views\n"
            f"• Save unlimited content\n"
            f"• Priority support\n"
            f"• No ads\n\n"
            f"Upgrade now: /subscribe"
        )
