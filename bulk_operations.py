"""
Bulk User Operations System
Perform operations on multiple users at once
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, and_
from database import SessionLocal, User, Payment, UserInteraction, Analytics
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BulkUserOperations:
    """Handle bulk operations on users"""
    
    def __init__(self, bot_application=None):
        self.bot = bot_application
        self.db = SessionLocal()
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    # ==================== QUERY OPERATIONS ====================
    
    def get_users_by_criteria(self, criteria):
        """
        Get users matching criteria
        
        Criteria examples:
        - {'is_premium': True}
        - {'created_at': {'after': datetime}}
        - {'subscription_end': {'before': datetime}}
        """
        query = self.db.query(User)
        
        for key, value in criteria.items():
            if isinstance(value, dict):
                # Handle date ranges
                if 'after' in value:
                    query = query.filter(getattr(User, key) >= value['after'])
                if 'before' in value:
                    query = query.filter(getattr(User, key) <= value['before'])
            else:
                query = query.filter(getattr(User, key) == value)
        
        return query.all()
    
    def get_inactive_users(self, days=30):
        """Get users inactive for X days"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return self.db.query(User).filter(
            or_(
                User.created_at < cutoff,
                User.created_at.is_(None)
            )
        ).all()
    
    def get_expiring_subscriptions(self, days=7):
        """Get users with subscriptions expiring in X days"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days)
        
        return self.db.query(User).filter(
            and_(
                User.is_premium == True,
                User.subscription_end.isnot(None),
                User.subscription_end >= now,
                User.subscription_end <= future
            )
        ).all()
    
    def get_free_users(self):
        """Get all free tier users"""
        return self.db.query(User).filter(User.is_premium == False).all()
    
    def get_pro_users(self):
        """Get all pro users"""
        return self.db.query(User).filter(User.is_premium == True).all()
    
    def get_users_by_activity(self, min_views=0):
        """Get users by activity level"""
        from sqlalchemy import func
        
        user_activity = self.db.query(
            Analytics.user_id,
            func.count(Analytics.id).label('view_count')
        ).group_by(Analytics.user_id).having(
            func.count(Analytics.id) >= min_views
        ).subquery()
        
        return self.db.query(User).join(
            user_activity,
            User.id == user_activity.c.user_id
        ).all()
    
    # ==================== BULK UPDATE OPERATIONS ====================
    
    def bulk_grant_pro(self, user_ids, days=30):
        """Grant pro to multiple users"""
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        for user_id in user_ids:
            try:
                user = self.db.query(User).filter(User.telegram_id == user_id).first()
                if user:
                    user.is_premium = True
                    user.subscription_end = datetime.now(timezone.utc) + timedelta(days=days)
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"User {user_id} not found")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"User {user_id}: {str(e)}")
        
        self.db.commit()
        return results
    
    def bulk_revoke_pro(self, user_ids):
        """Revoke pro from multiple users"""
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        for user_id in user_ids:
            try:
                user = self.db.query(User).filter(User.telegram_id == user_id).first()
                if user:
                    user.is_premium = False
                    user.subscription_end = None
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"User {user_id} not found")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"User {user_id}: {str(e)}")
        
        self.db.commit()
        return results
    
    def bulk_extend_subscription(self, user_ids, days=30):
        """Extend subscription for multiple users"""
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        for user_id in user_ids:
            try:
                user = self.db.query(User).filter(User.telegram_id == user_id).first()
                if user and user.is_premium:
                    if user.subscription_end:
                        user.subscription_end += timedelta(days=days)
                    else:
                        user.subscription_end = datetime.now(timezone.utc) + timedelta(days=days)
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"User {user_id} not pro or not found")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"User {user_id}: {str(e)}")
        
        self.db.commit()
        return results
    
    def bulk_ban_users(self, user_ids, reason="Violation of terms"):
        """Ban multiple users"""
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        for user_id in user_ids:
            try:
                user = self.db.query(User).filter(User.telegram_id == user_id).first()
                if user:
                    if hasattr(user, 'is_banned'):
                        user.is_banned = True
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"User {user_id}: Ban column not available")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"User {user_id} not found")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"User {user_id}: {str(e)}")
        
        self.db.commit()
        return results
    
    def bulk_unban_users(self, user_ids):
        """Unban multiple users"""
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        for user_id in user_ids:
            try:
                user = self.db.query(User).filter(User.telegram_id == user_id).first()
                if user:
                    if hasattr(user, 'is_banned'):
                        user.is_banned = False
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"User {user_id}: Ban column not available")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"User {user_id} not found")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"User {user_id}: {str(e)}")
        
        self.db.commit()
        return results
    
    # ==================== BULK MESSAGE OPERATIONS ====================
    
    async def bulk_message_users(self, user_ids, message, delay=0.05):
        """Send message to multiple users"""
        if not self.bot:
            return {'error': 'Bot application not provided'}
        
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        for user_id in user_ids:
            try:
                await self.bot.bot.send_message(
                    chat_id=user_id,
                    text=message
                )
                results['success'] += 1
                await asyncio.sleep(delay)  # Rate limiting
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"User {user_id}: {str(e)}")
        
        return results
    
    async def message_inactive_users(self, days=30, message=None, delay=0.05):
        """Message users inactive for X days"""
        users = self.get_inactive_users(days)
        
        if not message:
            message = (
                "👋 We miss you!\n\n"
                "Come back and check out the latest trending content.\n\n"
                "Use /start to explore!"
            )
        
        user_ids = [u.telegram_id for u in users]
        return await self.bulk_message_users(user_ids, message, delay)
    
    async def message_expiring_subscriptions(self, days=7, message=None, delay=0.05):
        """Message users with expiring subscriptions"""
        users = self.get_expiring_subscriptions(days)
        
        if not message:
            message = (
                "⚠️ Your Pro subscription is expiring soon!\n\n"
                "Renew now to keep enjoying unlimited access.\n\n"
                "Use /subscribe to renew."
            )
        
        user_ids = [u.telegram_id for u in users]
        return await self.bulk_message_users(user_ids, message, delay)
    
    async def message_free_users(self, message, delay=0.05):
        """Message all free tier users"""
        users = self.get_free_users()
        user_ids = [u.telegram_id for u in users]
        return await self.bulk_message_users(user_ids, message, delay)
    
    async def message_pro_users(self, message, delay=0.05):
        """Message all pro users"""
        users = self.get_pro_users()
        user_ids = [u.telegram_id for u in users]
        return await self.bulk_message_users(user_ids, message, delay)
    
    # ==================== BULK DELETE OPERATIONS ====================
    
    def bulk_delete_inactive_users(self, days=90):
        """Delete users inactive for X days"""
        users = self.get_inactive_users(days)
        count = len(users)
        
        for user in users:
            # Delete related data first
            self.db.query(UserInteraction).filter(
                UserInteraction.user_id == user.id
            ).delete()
            
            self.db.query(Analytics).filter(
                Analytics.user_id == user.id
            ).delete()
            
            self.db.query(Payment).filter(
                Payment.user_id == user.id
            ).delete()
            
            # Delete user
            self.db.delete(user)
        
        self.db.commit()
        return {'deleted': count}
    
    def bulk_delete_users(self, user_ids):
        """Delete specific users"""
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        for user_id in user_ids:
            try:
                user = self.db.query(User).filter(User.telegram_id == user_id).first()
                if user:
                    # Delete related data
                    self.db.query(UserInteraction).filter(
                        UserInteraction.user_id == user.id
                    ).delete()
                    
                    self.db.query(Analytics).filter(
                        Analytics.user_id == user.id
                    ).delete()
                    
                    self.db.query(Payment).filter(
                        Payment.user_id == user.id
                    ).delete()
                    
                    self.db.delete(user)
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"User {user_id} not found")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"User {user_id}: {str(e)}")
        
        self.db.commit()
        return results
    
    # ==================== EXPORT OPERATIONS ====================
    
    def export_users_csv(self, filename='users_export.csv', criteria=None):
        """Export users to CSV"""
        import csv
        
        if criteria:
            users = self.get_users_by_criteria(criteria)
        else:
            users = self.db.query(User).all()
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ID', 'Telegram ID', 'Username', 'Is Premium',
                'Subscription End', 'Created At'
            ])
            
            for user in users:
                writer.writerow([
                    user.id,
                    user.telegram_id,
                    user.username or 'N/A',
                    'Yes' if user.is_premium else 'No',
                    user.subscription_end.strftime('%Y-%m-%d') if user.subscription_end else 'N/A',
                    user.created_at.strftime('%Y-%m-%d') if user.created_at else 'N/A'
                ])
        
        return {'exported': len(users), 'file': filename}
    
    def export_user_stats(self, filename='user_stats.csv'):
        """Export user statistics"""
        import csv
        from sqlalchemy import func
        
        # Get user stats
        stats = self.db.query(
            User.telegram_id,
            User.username,
            User.is_premium,
            func.count(Analytics.id).label('total_views'),
            func.count(UserInteraction.id).label('total_interactions')
        ).outerjoin(Analytics, User.id == Analytics.user_id)\
         .outerjoin(UserInteraction, User.id == UserInteraction.user_id)\
         .group_by(User.id).all()
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Telegram ID', 'Username', 'Is Premium',
                'Total Views', 'Total Interactions'
            ])
            
            for stat in stats:
                writer.writerow([
                    stat.telegram_id,
                    stat.username or 'N/A',
                    'Yes' if stat.is_premium else 'No',
                    stat.total_views,
                    stat.total_interactions
                ])
        
        return {'exported': len(stats), 'file': filename}
    
    # ==================== STATISTICS ====================
    
    def get_bulk_statistics(self):
        """Get overall user statistics"""
        total_users = self.db.query(User).count()
        pro_users = self.db.query(User).filter(User.is_premium == True).count()
        free_users = total_users - pro_users
        
        # Active users (last 7 days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        active_users = self.db.query(Analytics.user_id).filter(
            Analytics.timestamp >= week_ago
        ).distinct().count()
        
        # Expiring soon (7 days)
        expiring = len(self.get_expiring_subscriptions(7))
        
        # Inactive (30 days)
        inactive = len(self.get_inactive_users(30))
        
        return {
            'total_users': total_users,
            'pro_users': pro_users,
            'free_users': free_users,
            'active_users_7d': active_users,
            'expiring_soon': expiring,
            'inactive_30d': inactive,
            'conversion_rate': f"{(pro_users/total_users*100):.1f}%" if total_users > 0 else "0%"
        }


# Convenience functions
def get_bulk_ops(bot_application=None):
    """Get bulk operations instance"""
    return BulkUserOperations(bot_application)
