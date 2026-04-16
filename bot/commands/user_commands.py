"""
User Commands Module
Handles all user-facing commands
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal, User
from datetime import datetime, timezone
import json
from ban_decorator import check_ban
from typing import Optional, List, Dict, Any


class UserCommands:
    """User command handlers"""
    
    def __init__(self, bot_instance: 'TrendLensBot') -> None:
        self.bot = bot_instance
    
    @check_ban
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        if not update.message:
            return
        
        user = update.effective_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                db_user = User(
                    telegram_id=user.id, 
                    username=user.username[:50] if user.username else None,
                    categories=json.dumps([])
                )
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
            
            # Notify admin of new user
            if self.bot.admin_id:
                try:
                    await context.bot.send_message(
                        chat_id=self.bot.admin_id,
                        text=f"🆕 New User\n\n👤 @{user.username or user.first_name}\n🆔 ID: {user.id}"
                    )
                except:
                    pass
            
            # Check if banned
            if hasattr(db_user, 'is_banned') and db_user.is_banned:
                await update.message.reply_text("⛔ You have been banned from using this bot.")
                return
            
            # Update last activity
            db_user.created_at = datetime.now(timezone.utc)
            db.commit()
            
            keyboard = [
                [InlineKeyboardButton("📂 Browse Categories", callback_data="categories")],
                [InlineKeyboardButton("⭐ Upgrade to Pro", callback_data="subscribe")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
            ]
            
            status = '✨ Pro Member' if db_user.is_premium else '🆓 Free Member'
            
            text = (
                "🔥 Welcome to TrendLens AI!\n\n"
                "🎯 What We Do:\n"
                "Discover VIRAL & TRENDING content from Reddit, YouTube, Twitter, TikTok, Instagram, Facebook and news sources - all in one place!\n\n"
                "⚡ Why TrendLens?\n"
                "We show you ONLY the most viral posts with high views, most comments, and top engagement - NO random content!\n\n"
                "📱 Categories Available:\n"
                "• 😂 Memes - Viral & funny content\n"
                "• 🎮 Gaming - Latest game news & updates\n"
                "• 💻 Tech - AI, gadgets, programming\n"
                "• ⚽ Sports - Premier League, NBA, more\n"
                "• 🎬 Entertainment - Movies, TV shows\n"
                "• 📰 News - Breaking news worldwide\n"
                "• 💼 Jobs - Remote & freelance opportunities\n\n"
                f"👤 Your Status: {status}\n\n"
                "💡 Quick Start: Click 'Browse Categories' below!"
            )
            
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        finally:
            db.close()
    
    @check_ban
    async def account(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /account command"""
        user = update.effective_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if db_user.is_premium and db_user.subscription_end:
                sub_end = db_user.subscription_end
                if sub_end.tzinfo is None:
                    sub_end = sub_end.replace(tzinfo=timezone.utc)
                
                if sub_end > datetime.now(timezone.utc):
                    days_left = (sub_end - datetime.now(timezone.utc)).days
                    status = f"✨ Pro Member\n⏰ {days_left} days remaining\n📅 Expires: {sub_end.strftime('%Y-%m-%d')}"
                else:
                    status = "🆓 Free Tier\n\nUpgrade to Pro: /subscribe"
            else:
                status = "🆓 Free Tier\n\nUpgrade to Pro: /subscribe"
            
            await update.message.reply_text(
                f"👤 Account Status\n\n"
                f"🆔 User ID: {user.id}\n"
                f"👤 Username: @{user.username or user.first_name}\n\n"
                f"{status}"
            )
        finally:
            db.close()
    
    @check_ban
    async def saved(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /saved command"""
        from database import UserInteraction, Content
        
        user = update.effective_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await update.message.reply_text("❌ User not found. Use /start first.")
                return
            
            if not db_user.is_premium:
                await update.message.reply_text(
                    "⭐ Saved Content is a Pro feature!\n\n"
                    "✅ What you get:\n"
                    "• Save unlimited content\n"
                    "• Access anytime\n"
                    "• Organize bookmarks\n\n"
                    "Upgrade now: /subscribe"
                )
                return
            
            interactions = db.query(UserInteraction).filter(
                UserInteraction.user_id == db_user.id,
                UserInteraction.action == 'save'
            ).order_by(UserInteraction.timestamp.desc()).limit(20).all()
            
            if not interactions:
                await update.message.reply_text(
                    "💾 No saved content yet!\n\n"
                    "💡 How to save:\n"
                    "1. Browse any category\n"
                    "2. Click 💾 Save button\n"
                    "3. Access here anytime\n\n"
                    "Start browsing: /start"
                )
                return
            
            contents = []
            for interaction in interactions:
                content = db.query(Content).filter(Content.id == interaction.content_id).first()
                if content:
                    contents.append({
                        'id': content.id, 'title': content.title, 'url': content.url,
                        'platform': content.platform, 'category': content.category,
                        'thumbnail': content.thumbnail, 'description': content.description
                    })
            
            if not contents:
                await update.message.reply_text(
                    "⚠️ Saved content no longer available.\n\n"
                    "Content may have been removed or expired.\n\n"
                    "Browse fresh content: /start"
                )
                return
            
            context.user_data['contents'] = contents
            context.user_data['index'] = 0
            context.user_data['saved_view'] = True
            
            # Send first saved content
            content = contents[0]
            caption = f"💾 Saved Content\n\n📌 {content['title']}\n\n"
            caption += f"📂 {content['category'].title()}\n"
            caption += f"🔗 {content['platform'].upper()}\n"
            if content.get('description'):
                caption += f"📝 {content['description'][:150]}...\n\n"
            caption += f"🌐 {content['url']}\n\n"
            caption += f"📊 1/{len(contents)}"
            
            # Navigation buttons
            keyboard = []
            nav_row = []
            if len(contents) > 1:
                nav_row.append(InlineKeyboardButton("Next ➡️", callback_data="saved_nav_next"))
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("« Back to Menu", callback_data="start")])
            
            try:
                if content.get('thumbnail'):
                    await update.message.reply_photo(
                        photo=content['thumbnail'],
                        caption=caption,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await update.message.reply_text(
                        caption,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            except Exception as e:
                import logging
                logging.error(f"Send saved content error: {e}")
                await update.message.reply_text(
                    caption,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            import logging
            logging.error(f"Saved content error: {e}")
            await update.message.reply_text(
                "❌ Failed to load saved content.\n\n"
                "Please try again or contact support."
            )
        finally:
            db.close()
    
    @check_ban
    async def trending(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /trending command"""
        category = context.args[0] if context.args else 'memes'
        
        if category not in self.bot.categories:
            await update.message.reply_text(f"Invalid category. Choose from: {', '.join(self.bot.categories)}")
            return
        
        user = update.effective_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            limit = 20 if db_user.is_premium else 30
            cached = []
            if self.bot.redis:
                try:
                    cached = self.bot.redis.zrevrange(f"trending:{category}", 0, limit-1)
                except:
                    pass
            
            if cached:
                contents = [json.loads(c) for c in cached]
                text = f"🔥 Top {category.title()} Trends:\n\n"
                for i, c in enumerate(contents[:limit], 1):
                    text += f"{i}. {c['title'][:50]}...\n   {c['url']}\n\n"
                
                await update.message.reply_text(text)
            else:
                await update.message.reply_text("No trends available. Try again later!")
        finally:
            db.close()

    @check_ban
    async def limit_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Check rate limit status"""
        from bot.services.rate_limit_service import RateLimitService
        
        user = update.effective_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await update.message.reply_text("❌ User not found. Use /start first.")
                return
            
            # Get rate limit status
            allowed, used, limit = RateLimitService.check_rate_limit(user.id)
            
            # Format message
            message = RateLimitService.format_limit_message(used, limit, db_user.is_premium)
            
            await update.message.reply_text(message)
        finally:
            db.close()

    @check_ban
    async def live_sports(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get live sports events"""
        summary = await self.bot.realtime_updates.get_live_sports_summary()
        await update.message.reply_text(summary)
    
    @check_ban
    async def breaking_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get breaking news"""
        summary = await self.bot.realtime_updates.get_breaking_news_summary()
        await update.message.reply_text(summary)
