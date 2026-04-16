"""
Admin User Management Module
Handles user management commands for admins
"""

from telegram import Update
from telegram.ext import ContextTypes
from database import SessionLocal, User
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AdminUserManagement:
    """Admin user management command handlers"""
    
    def __init__(self, bot_instance: 'TrendLensBot') -> None:
        self.bot = bot_instance
    
    def _is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id == self.bot.admin_id
    
    async def grant_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Grant Pro membership to a user"""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: /grant_pro <user_id> [days]\n\n"
                "Example:\n"
                "/grant_pro 123456789 30\n"
                "/grant_pro 123456789  (default: 30 days)"
            )
            return
        
        try:
            target_user_id = int(context.args[0])
            days = int(context.args[1]) if len(context.args) > 1 else 30
            
            db = SessionLocal()
            try:
                db_user = db.query(User).filter(User.telegram_id == target_user_id).first()
                
                if not db_user:
                    await update.message.reply_text(f"❌ User {target_user_id} not found in database.")
                    return
                
                # Grant Pro membership
                db_user.is_premium = True
                db_user.subscription_end = datetime.now(timezone.utc) + timedelta(days=days)
                db.commit()
                
                # Notify admin
                await update.message.reply_text(
                    f"✅ Pro membership granted!\n\n"
                    f"👤 User ID: {target_user_id}\n"
                    f"📅 Duration: {days} days\n"
                    f"⏰ Expires: {db_user.subscription_end.strftime('%Y-%m-%d')}\n\n"
                    f"User will have unlimited access until expiration."
                )
                
                # Notify user
                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            f"🎉 Congratulations!\n\n"
                            f"You've been granted Pro membership!\n\n"
                            f"✨ Benefits:\n"
                            f"• Unlimited content access\n"
                            f"• Save unlimited content\n"
                            f"• Priority support\n"
                            f"• No ads\n\n"
                            f"📅 Valid for: {days} days\n"
                            f"⏰ Expires: {db_user.subscription_end.strftime('%Y-%m-%d')}\n\n"
                            f"Enjoy your Pro features! 🚀"
                        )
                    )
                except Exception as e:
                    logger.warning(f"Could not notify user {target_user_id}: {e}")
                
            finally:
                db.close()
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID or days. Must be numbers.")
        except Exception as e:
            logger.error(f"Error granting Pro: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def revoke_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Revoke Pro membership from a user"""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: /revoke_pro <user_id>\n\n"
                "Example: /revoke_pro 123456789"
            )
            return
        
        try:
            target_user_id = int(context.args[0])
            
            db = SessionLocal()
            try:
                db_user = db.query(User).filter(User.telegram_id == target_user_id).first()
                
                if not db_user:
                    await update.message.reply_text(f"❌ User {target_user_id} not found in database.")
                    return
                
                if not db_user.is_premium:
                    await update.message.reply_text(f"ℹ️ User {target_user_id} is not a Pro member.")
                    return
                
                # Revoke Pro membership
                db_user.is_premium = False
                db_user.subscription_end = None
                db.commit()
                
                # Notify admin
                await update.message.reply_text(
                    f"✅ Pro membership revoked!\n\n"
                    f"👤 User ID: {target_user_id}\n"
                    f"📊 Status: Free Tier\n\n"
                    f"User now has limited access."
                )
                
                # Notify user
                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            f"ℹ️ Your Pro membership has been revoked.\n\n"
                            f"You now have Free Tier access:\n"
                            f"• Limited content views\n"
                            f"• Basic features\n\n"
                            f"To upgrade again, use /subscribe"
                        )
                    )
                except Exception as e:
                    logger.warning(f"Could not notify user {target_user_id}: {e}")
                
            finally:
                db.close()
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
        except Exception as e:
            logger.error(f"Error revoking Pro: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ban a user from using the bot"""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: /ban_user <user_id> [reason]\n\n"
                "Example:\n"
                "/ban_user 123456789 Spam\n"
                "/ban_user 123456789"
            )
            return
        
        try:
            target_user_id = int(context.args[0])
            reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
            
            # Prevent banning admin
            if target_user_id == self.bot.admin_id:
                await update.message.reply_text("❌ Cannot ban admin!")
                return
            
            db = SessionLocal()
            try:
                db_user = db.query(User).filter(User.telegram_id == target_user_id).first()
                
                if not db_user:
                    await update.message.reply_text(f"❌ User {target_user_id} not found in database.")
                    return
                
                if hasattr(db_user, 'is_banned') and db_user.is_banned:
                    await update.message.reply_text(f"ℹ️ User {target_user_id} is already banned.")
                    return
                
                # Ban user
                db_user.is_banned = True
                db.commit()
                
                # Notify admin
                await update.message.reply_text(
                    f"✅ User banned!\n\n"
                    f"👤 User ID: {target_user_id}\n"
                    f"📝 Reason: {reason}\n"
                    f"⛔ Status: Banned\n\n"
                    f"User cannot use the bot anymore."
                )
                
                # Notify user
                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            f"⛔ You have been banned from using this bot.\n\n"
                            f"Reason: {reason}\n\n"
                            f"If you believe this is a mistake, contact support."
                        )
                    )
                except Exception as e:
                    logger.warning(f"Could not notify user {target_user_id}: {e}")
                
            finally:
                db.close()
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Unban a user"""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: /unban_user <user_id>\n\n"
                "Example: /unban_user 123456789"
            )
            return
        
        try:
            target_user_id = int(context.args[0])
            
            db = SessionLocal()
            try:
                db_user = db.query(User).filter(User.telegram_id == target_user_id).first()
                
                if not db_user:
                    await update.message.reply_text(f"❌ User {target_user_id} not found in database.")
                    return
                
                if not hasattr(db_user, 'is_banned') or not db_user.is_banned:
                    await update.message.reply_text(f"ℹ️ User {target_user_id} is not banned.")
                    return
                
                # Unban user
                db_user.is_banned = False
                db.commit()
                
                # Notify admin
                await update.message.reply_text(
                    f"✅ User unbanned!\n\n"
                    f"👤 User ID: {target_user_id}\n"
                    f"✅ Status: Active\n\n"
                    f"User can now use the bot again."
                )
                
                # Notify user
                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            f"✅ You have been unbanned!\n\n"
                            f"You can now use the bot again.\n"
                            f"Use /start to begin."
                        )
                    )
                except Exception as e:
                    logger.warning(f"Could not notify user {target_user_id}: {e}")
                
            finally:
                db.close()
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def user_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get detailed information about a user"""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: /user_info <user_id>\n\n"
                "Example: /user_info 123456789"
            )
            return
        
        try:
            target_user_id = int(context.args[0])
            
            db = SessionLocal()
            try:
                db_user = db.query(User).filter(User.telegram_id == target_user_id).first()
                
                if not db_user:
                    await update.message.reply_text(f"❌ User {target_user_id} not found in database.")
                    return
                
                # Get user stats
                from database import UserInteraction
                total_views = db.query(UserInteraction).filter(
                    UserInteraction.user_id == db_user.id,
                    UserInteraction.action == 'view'
                ).count()
                
                total_saves = db.query(UserInteraction).filter(
                    UserInteraction.user_id == db_user.id,
                    UserInteraction.action == 'save'
                ).count()
                
                # Build info message
                status = "✨ Pro Member" if db_user.is_premium else "🆓 Free Tier"
                banned_status = "⛔ Banned" if hasattr(db_user, 'is_banned') and db_user.is_banned else "✅ Active"
                
                info_text = (
                    f"👤 User Information\n\n"
                    f"🆔 User ID: {db_user.telegram_id}\n"
                    f"👤 Username: @{db_user.username or 'Not set'}\n"
                    f"📊 Status: {status}\n"
                    f"🚦 Account: {banned_status}\n"
                    f"📅 Joined: {db_user.created_at.strftime('%Y-%m-%d') if db_user.created_at else 'Unknown'}\n\n"
                    f"📈 Statistics:\n"
                    f"👁️ Total Views: {total_views}\n"
                    f"💾 Total Saves: {total_saves}\n"
                )
                
                if db_user.is_premium and db_user.subscription_end:
                    if db_user.subscription_end > datetime.now(timezone.utc):
                        days_left = (db_user.subscription_end - datetime.now(timezone.utc)).days
                        info_text += f"\n⏰ Pro Expires: {db_user.subscription_end.strftime('%Y-%m-%d')} ({days_left} days left)"
                    else:
                        info_text += f"\n⚠️ Pro Expired: {db_user.subscription_end.strftime('%Y-%m-%d')}"
                
                await update.message.reply_text(info_text)
                
            finally:
                db.close()
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
