"""
Callback Handlers Module
Handles all inline button callbacks
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal, User
from ban_decorator import check_ban
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from bot.services.rate_limit_service import RateLimitService


class CallbackHandlers:
    """Callback query handlers"""
    
    def __init__(self, bot_instance: 'TrendLensBot') -> None:
        self.bot = bot_instance
    
    async def _safe_edit_or_send(
        self, 
        query: Update.callback_query, 
        text: str, 
        keyboard: List[List[InlineKeyboardButton]]
    ) -> None:
        """Helper to safely edit message or send new one if photo exists"""
        try:
            if query.message.photo:
                await query.message.delete()
                await query.message.chat.send_message(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            import logging
            logging.error(f"Message edit error: {e}")
            try:
                await query.message.delete()
                await query.message.chat.send_message(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                pass
    
    async def _get_user(self, user_id: int, db: Session) -> User:
        """Helper to get or create user"""
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            db_user = User(
                telegram_id=user_id,
                username=None,
                categories=json.dumps([])
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        return db_user
    
    async def _check_banned(self, query: Update.callback_query, db_user: User) -> bool:
        """Helper to check if user is banned"""
        if hasattr(db_user, 'is_banned') and db_user.is_banned:
            await query.edit_message_text("⛔ You have been banned from using this bot.")
            return True
        return False
    
    @check_ban
    async def start_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle start button callback"""
        query = update.callback_query
        await query.answer()
        
        db = SessionLocal()
        try:
            db_user = await self._get_user(query.from_user.id, db)
            if await self._check_banned(query, db_user):
                return
            
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
            
            await self._safe_edit_or_send(query, text, keyboard)
        finally:
            db.close()
    
    @check_ban
    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle categories button callback"""
        query = update.callback_query
        await query.answer()
        
        db = SessionLocal()
        try:
            db_user = await self._get_user(query.from_user.id, db)
            if await self._check_banned(query, db_user):
                return
            
            keyboard = [
                [InlineKeyboardButton("😂 Memes / Comedy", callback_data="cat_memes")],
                [InlineKeyboardButton("⚽ Sports", callback_data="cat_sports")], 
                [InlineKeyboardButton("🎵 Entertainment", callback_data="cat_entertainment")],
                [InlineKeyboardButton("🎮 Gaming", callback_data="cat_gaming")],
                [InlineKeyboardButton("💻 Tech & Gadgets", callback_data="cat_tech")],
                [InlineKeyboardButton("💼 Jobs & Freelance", callback_data="cat_jobs")],
                [InlineKeyboardButton("📰 News & Events", callback_data="cat_news")],
                [InlineKeyboardButton("« Back", callback_data="start")]
            ]
            
            text = (
                "📂 Select a category to view trending content:\n\n"
                "🎯 Each category contains only relevant content - no mixing!"
            )
            
            await self._safe_edit_or_send(query, text, keyboard)
        finally:
            db.close()
    
    @check_ban
    async def navigate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle navigation button callbacks"""
        query = update.callback_query
        await query.answer()
        
        direction = query.data.split('_')[1]
        contents = context.user_data.get('contents', [])
        index = context.user_data.get('index', 0)
        
        if not contents:
            await query.answer("❌ No content available. Browse categories first.", show_alert=True)
            return
        
        if direction == 'next' and index < len(contents) - 1:
            index += 1
        elif direction == 'prev' and index > 0:
            index -= 1
        else:
            await query.answer("⚠️ No more items in this direction.", show_alert=True)
            return
        
        context.user_data['index'] = index
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if index < len(contents):
                content = contents[index]
                await self.send_content(query, content, index, len(contents), db_user.is_premium)
        except Exception as e:
            import logging
            logging.error(f"Navigation error: {e}")
            await query.answer("❌ Error loading content. Try again.", show_alert=True)
        finally:
            db.close()
    
    @check_ban
    async def show_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle category selection"""
        from database import Content
        from datetime import datetime, timezone, timedelta
        
        query = update.callback_query
        await query.answer()
        
        parts = query.data.split('_')
        category = parts[1] if len(parts) > 1 else None
        
        # Special handling for tech category - show subcategories
        if category == 'tech':
            await self.show_tech_subcategories(update, context)
            return
        
        # Special handling for sports category - show leagues
        if category == 'sports':
            await self.show_sports_leagues(update, context)
            return
        
        if not category or category not in self.bot.categories:
            await query.answer("❌ Invalid category", show_alert=True)
            return
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await query.answer("❌ User not found. Use /start first.", show_alert=True)
                return
            
            # Check rate limit
            allowed, used, limit = RateLimitService.check_rate_limit(user.id)
            
            if not allowed:
                # Rate limit exceeded
                message = RateLimitService.get_limit_exceeded_message()
                keyboard = [
                    [InlineKeyboardButton("⭐ Upgrade to Pro", callback_data="subscribe")],
                    [InlineKeyboardButton("« Back", callback_data="categories")]
                ]
                await self._safe_edit_or_send(query, message, keyboard)
                return
            
            # Get trending content
            cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
            limit_count = 20 if db_user.is_premium else 10
            
            contents = db.query(Content).filter(
                Content.category == category,
                Content.created_at >= cutoff,
                Content.thumbnail.isnot(None)
            ).order_by(Content.trend_score.desc()).limit(limit_count).all()
            
            if not contents:
                keyboard = [[InlineKeyboardButton("« Back", callback_data="categories")]]
                await query.edit_message_text(
                    f"No trending content found for {category}.\n\nTry again later!",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            # Store in context
            context.user_data['category'] = category
            context.user_data['contents'] = [{
                'id': c.id, 'title': c.title, 'url': c.url,
                'platform': c.platform, 'category': c.category,
                'thumbnail': c.thumbnail, 'description': c.description,
                'trend_score': c.trend_score
            } for c in contents]
            context.user_data['index'] = 0
            
            # Track view for rate limiting
            if contents:
                RateLimitService.track_view(db_user.id, contents[0].id)
            
            # Send first content
            await self.send_content(query, context.user_data['contents'][0], 0, len(contents), db_user.is_premium)
        finally:
            db.close()
    
    @check_ban
    async def show_tech_subcategories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show tech subcategories"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🤖 AI & Data", callback_data="techcat_ai_data")],
            [InlineKeyboardButton("💻 Software & Web", callback_data="techcat_software")],
            [InlineKeyboardButton("🔒 Cyber & Cloud", callback_data="techcat_cyber")],
            [InlineKeyboardButton("⚙️ Hardware & Robotics", callback_data="techcat_hardware")],
            [InlineKeyboardButton("🚀 Emerging Tech", callback_data="techcat_emerging")],
            [InlineKeyboardButton("« Back", callback_data="categories")]
        ]
        
        text = "💻 Tech Categories:\n\n🎯 Select a specific tech area:"
        await self._safe_edit_or_send(query, text, keyboard)
    
    @check_ban
    async def show_sports_leagues(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show sports league selection"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("⚽ Premier League (England)", callback_data="league_premier_league")],
            [InlineKeyboardButton("⚽ La Liga (Spain)", callback_data="league_la_liga")],
            [InlineKeyboardButton("⚽ Bundesliga (Germany)", callback_data="league_bundesliga")],
            [InlineKeyboardButton("⚽ Serie A (Italy)", callback_data="league_serie_a")],
            [InlineKeyboardButton("⚽ Ligue 1 (France)", callback_data="league_ligue_1")],
            [InlineKeyboardButton("🏆 Champions League", callback_data="league_champions_league")],
            [InlineKeyboardButton("🏆 Europa League", callback_data="league_europa_league")],
            [InlineKeyboardButton("🏀 NBA (Basketball)", callback_data="league_nba")],
            [InlineKeyboardButton("🏈 NFL (American Football)", callback_data="league_nfl")],
            [InlineKeyboardButton("🎯 All Sports", callback_data="league_all_sports")],
            [InlineKeyboardButton("« Back", callback_data="categories")]
        ]
        
        text = (
            "⚽ Select Your Favorite League:\n\n"
            "🎯 Get trending content from your league\n"
            "⚡ LIVE goal alerts (Pro members)\n"
            "🏆 Best goals, highlights & moments\n\n"
            "💡 Pro Tip: Subscribe to get instant notifications when your team scores!"
        )
        
        await self._safe_edit_or_send(query, text, keyboard)
    
    @check_ban
    async def show_tech_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show tech subcategory content"""
        from database import Content
        from datetime import datetime, timezone, timedelta
        
        query = update.callback_query
        await query.answer()
        
        # Parse subcategory from callback data
        parts = query.data.split('_')
        if len(parts) >= 3:
            subcategory = '_'.join(parts[1:])
        else:
            subcategory = parts[1] if len(parts) > 1 else ''
        
        if subcategory not in self.bot.tech_subcategories:
            await query.answer("❌ Invalid subcategory", show_alert=True)
            return
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await query.answer("❌ User not found. Use /start first.", show_alert=True)
                return
            
            # Get tech keywords for this subcategory
            keywords = self.bot.tech_keywords.get(subcategory, [])
            
            # Get trending tech content
            cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
            limit = 20 if db_user.is_premium else 10
            
            # Query tech category content
            all_tech_contents = db.query(Content).filter(
                Content.category == 'tech',
                Content.created_at >= cutoff,
                Content.thumbnail.isnot(None)
            ).order_by(Content.trend_score.desc()).limit(200).all()
            
            # Strict filtering by subcategory keywords with scoring
            contents = []
            for c in all_tech_contents:
                text = f"{c.title} {c.description or ''}".lower()
                
                # Count keyword matches for this subcategory
                match_score = 0
                matched_keywords = []
                for kw in keywords:
                    if kw.lower() in text:
                        match_score += 1
                        matched_keywords.append(kw)
                
                # Only include if it has at least one keyword match
                if match_score > 0:
                    # Check if it matches OTHER subcategories better
                    other_match_score = 0
                    for other_subcat, other_keywords in self.bot.tech_keywords.items():
                        if other_subcat != subcategory:
                            for other_kw in other_keywords:
                                if other_kw.lower() in text:
                                    other_match_score += 1
                    
                    # Only add if this subcategory has equal or better match
                    # OR if match_score is strong (2+ keywords)
                    if match_score >= other_match_score or match_score >= 2:
                        contents.append({
                            'id': c.id, 'title': c.title, 'url': c.url,
                            'platform': c.platform, 'category': c.category,
                            'thumbnail': c.thumbnail, 'description': c.description,
                            'trend_score': c.trend_score,
                            'match_score': match_score,
                            'matched_keywords': matched_keywords
                        })
            
            # Sort by match score first, then trend score
            contents.sort(key=lambda x: (x['match_score'], x['trend_score']), reverse=True)
            contents = contents[:limit]
            
            if not contents:
                keyboard = [[InlineKeyboardButton("« Back", callback_data="cat_tech")]]
                text_msg = f"No trending content found for {self.bot.tech_subcategories[subcategory]}.\n\nTry again later!"
                try:
                    if query.message.photo:
                        await query.message.delete()
                        await query.message.chat.send_message(
                            text=text_msg,
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    else:
                        await query.edit_message_text(
                            text_msg,
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                except:
                    pass
                return
            
            # Store in context
            context.user_data['category'] = 'tech'
            context.user_data['subcategory'] = subcategory
            context.user_data['contents'] = contents
            context.user_data['index'] = 0
            
            # Send first content
            await self.send_content(query, contents[0], 0, len(contents), db_user.is_premium)
        finally:
            db.close()
    
    @check_ban
    async def show_league_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show content for specific sports league"""
        from database import Content
        from datetime import datetime, timezone, timedelta
        
        query = update.callback_query
        await query.answer()
        
        # Parse league from callback data
        league = query.data.replace('league_', '')
        
        if league not in self.bot.sports_leagues:
            await query.answer("❌ Invalid league", show_alert=True)
            return
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = await self._get_user(user.id, db)
            
            if not db_user:
                await query.answer("❌ User not found. Use /start first.", show_alert=True)
                return
            
            # Get league keywords
            keywords = self.bot.sports_keywords.get(league, [])
            
            # Get trending sports content
            cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
            limit = 20 if db_user.is_premium else 10
            
            # Query sports category content
            all_sports_contents = db.query(Content).filter(
                Content.category == 'sports',
                Content.created_at >= cutoff,
                Content.thumbnail.isnot(None)
            ).order_by(Content.trend_score.desc()).limit(200).all()
            
            # Filter by league keywords with strict scoring
            contents = []
            for c in all_sports_contents:
                text = f"{c.title} {c.description or ''}".lower()
                
                # For "all_sports", include everything
                if league == 'all_sports':
                    contents.append({
                        'id': c.id, 'title': c.title, 'url': c.url,
                        'platform': c.platform, 'category': c.category,
                        'thumbnail': c.thumbnail, 'description': c.description,
                        'trend_score': c.trend_score
                    })
                    if len(contents) >= limit:
                        break
                    continue
                
                # Count keyword matches for this league
                match_score = 0
                matched_keywords = []
                for kw in keywords:
                    if kw.lower() in text:
                        match_score += 1
                        matched_keywords.append(kw)
                
                # Only include if it has at least one keyword match
                if match_score > 0:
                    # Check if it matches OTHER leagues better
                    other_match_score = 0
                    for other_league, other_keywords in self.bot.sports_keywords.items():
                        if other_league != league and other_league != 'all_sports':
                            for other_kw in other_keywords:
                                if other_kw.lower() in text:
                                    other_match_score += 1
                    
                    # Only add if this league has equal or better match
                    # OR if match_score is strong (2+ keywords)
                    if match_score >= other_match_score or match_score >= 2:
                        contents.append({
                            'id': c.id, 'title': c.title, 'url': c.url,
                            'platform': c.platform, 'category': c.category,
                            'thumbnail': c.thumbnail, 'description': c.description,
                            'trend_score': c.trend_score,
                            'match_score': match_score,
                            'matched_keywords': matched_keywords
                        })
            
            # Sort by match score first, then trend score
            if league != 'all_sports':
                contents.sort(key=lambda x: (x.get('match_score', 0), x['trend_score']), reverse=True)
            contents = contents[:limit]
            
            if not contents:
                keyboard = [[InlineKeyboardButton("« Back", callback_data="cat_sports")]]
                text_msg = f"No trending content found for {self.bot.sports_leagues[league]}.\n\nTry again later!"
                await self._safe_edit_or_send(query, text_msg, keyboard)
                return
            
            # Store in context
            context.user_data['category'] = 'sports'
            context.user_data['league'] = league
            context.user_data['contents'] = contents
            context.user_data['index'] = 0
            
            # Send first content
            await self.send_content(query, contents[0], 0, len(contents), db_user.is_premium)
        finally:
            db.close()
    
    async def send_content(self, query, content, index, total, is_premium):
        """Send content with navigation buttons"""
        title = content.get('title', 'No title')
        url = content.get('url', '')
        platform = content.get('platform', 'Unknown')
        thumbnail = content.get('thumbnail')
        
        text = f"📊 {index + 1}/{total}\n\n"
        text += f"📌 {title}\n\n"
        text += f"🔗 Platform: {platform}\n"
        text += f"🌐 {url}"
        
        # Navigation buttons
        buttons = []
        nav_row = []
        if index > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data="nav_prev"))
        if index < total - 1:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data="nav_next"))
        if nav_row:
            buttons.append(nav_row)
        
        # Time filter buttons
        time_filter_row = [
            InlineKeyboardButton("⏰ 24h", callback_data="filter_24h"),
            InlineKeyboardButton("⏰ 48h", callback_data="filter_48h"),
            InlineKeyboardButton("⏰ Week", callback_data="filter_week")
        ]
        buttons.append(time_filter_row)
        
        if is_premium:
            buttons.append([InlineKeyboardButton("💾 Save", callback_data=f"save_{index}")])
        
        buttons.append([InlineKeyboardButton("« Back", callback_data="categories")])
        
        try:
            # Check if current message has photo
            if query.message.photo:
                # Delete old message and send new one
                if thumbnail:
                    await query.message.delete()
                    await query.message.chat.send_photo(
                        photo=thumbnail,
                        caption=text,
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    await query.message.delete()
                    await query.message.chat.send_message(
                        text=text,
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
            else:
                # Text message - can edit
                if thumbnail:
                    await query.message.delete()
                    await query.message.chat.send_photo(
                        photo=thumbnail,
                        caption=text,
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            import logging
            logging.error(f"Send content error: {e}")
            # Fallback: delete and send new
            try:
                await query.message.delete()
                if thumbnail:
                    await query.message.chat.send_photo(
                        photo=thumbnail,
                        caption=text,
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    await query.message.chat.send_message(
                        text=text,
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
            except:
                pass
    
    async def save_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle save button callback"""
        from database import UserInteraction
        
        query = update.callback_query
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user.is_premium:
                await query.answer("⭐ Pro feature! Upgrade to save content.", show_alert=True)
                return
            
            try:
                index = int(query.data.split('_')[1])
                contents = context.user_data.get('contents', [])
                
                if index < len(contents):
                    content = contents[index]
                    
                    if isinstance(content, dict):
                        content_id = content.get('id')
                    else:
                        content_id = content.id
                    
                    if content_id:
                        existing = db.query(UserInteraction).filter(
                            UserInteraction.user_id == db_user.id,
                            UserInteraction.content_id == content_id,
                            UserInteraction.action == 'save'
                        ).first()
                        
                        if not existing:
                            interaction = UserInteraction(
                                user_id=db_user.id,
                                content_id=content_id,
                                action='save'
                            )
                            db.add(interaction)
                            db.commit()
                            
                            from bot.services.analytics_service import AnalyticsService
                            analytics = AnalyticsService(self.bot)
                            analytics.track_event(db, db_user.id, 'content_save', metadata={'content_id': content_id})
                            
                            await query.answer("✅ Saved!", show_alert=True)
                        else:
                            await query.answer("Already saved!", show_alert=True)
                    else:
                        await query.answer("❌ Cannot save", show_alert=True)
                else:
                    await query.answer("❌ Not found", show_alert=True)
            except Exception as e:
                await query.answer("❌ Error saving", show_alert=True)
        finally:
            db.close()
    
    @check_ban
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu"""
        query = update.callback_query
        await query.answer()
        
        db = SessionLocal()
        try:
            db_user = await self._get_user(query.from_user.id, db)
            if await self._check_banned(query, db_user):
                return
            
            status = '✨ Pro Member' if db_user.is_premium else '🆓 Free Member'
            
            keyboard = [
                [InlineKeyboardButton("👤 Account Info", callback_data="account_info")],
                [InlineKeyboardButton("💾 Saved Content", callback_data="view_saved")],
                [InlineKeyboardButton("📊 My Statistics", callback_data="my_stats")],
                [InlineKeyboardButton("🔔 Notifications", callback_data="notifications_settings")],
                [InlineKeyboardButton("❓ Help & Support", callback_data="help_support")],
                [InlineKeyboardButton("« Back", callback_data="start")]
            ]
            
            text = f"⚙️ Settings\n\n👤 Status: {status}\n\nManage your preferences:"
            await self._safe_edit_or_send(query, text, keyboard)
        finally:
            db.close()
    
    @check_ban
    async def account_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show account information"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            status = '✨ Pro Member' if db_user.is_premium else '🆓 Free Member'
            joined = db_user.created_at.strftime('%Y-%m-%d') if db_user.created_at else 'Unknown'
            
            text = (
                f"👤 Account Information\n\n"
                f"🆔 User ID: {user.id}\n"
                f"📛 Username: @{user.username or 'Not set'}\n"
                f"🏷️ Status: {status}\n"
                f"📅 Joined: {joined}\n\n"
                f"💡 Upgrade to Pro for unlimited access!"
            )
            
            keyboard = [[InlineKeyboardButton("« Back", callback_data="settings")]]
            
            try:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
        finally:
            db.close()
    
    @check_ban
    async def view_saved(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View saved content"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user.is_premium:
                await query.answer("⭐ Pro feature! Upgrade to save content.", show_alert=True)
                return
            
            text = "💾 Saved Content\n\nUse /saved command to view your saved items."
            keyboard = [[InlineKeyboardButton("« Back", callback_data="settings")]]
            
            try:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
        finally:
            db.close()
    
    @check_ban
    async def my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user statistics"""
        from database import UserInteraction
        
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            # Count interactions
            total_views = db.query(UserInteraction).filter(
                UserInteraction.user_id == db_user.id,
                UserInteraction.action == 'view'
            ).count()
            
            total_saves = db.query(UserInteraction).filter(
                UserInteraction.user_id == db_user.id,
                UserInteraction.action == 'save'
            ).count()
            
            text = (
                f"📊 Your Statistics\n\n"
                f"👁️ Total Views: {total_views}\n"
                f"💾 Total Saves: {total_saves}\n\n"
                f"📅 Member since: {db_user.created_at.strftime('%Y-%m-%d') if db_user.created_at else 'Unknown'}"
            )
            
            keyboard = [[InlineKeyboardButton("« Back", callback_data="settings")]]
            
            try:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
        finally:
            db.close()
    
    @check_ban
    async def notifications_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show notifications settings"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "🔔 Notification Settings\n\n"
            "📢 Manage notifications:\n"
            "- Trending alerts\n"
            "- New content updates\n"
            "- Pro features\n\n"
            "⚙️ Manage via Telegram settings"
        )
        
        keyboard = [[InlineKeyboardButton("« Back", callback_data="settings")]]
        
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            pass
    
    @check_ban
    async def help_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help and support"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "❓ Help & Support\n\n"
            "📚 Commands:\n"
            "/start - Main menu\n"
            "/account - Account info\n"
            "/saved - Saved content\n"
            "/trending - Trending now\n\n"
            "💬 Need help? Contact support!"
        )
        
        keyboard = [[InlineKeyboardButton("« Back", callback_data="settings")]]
        
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            pass
    
    @check_ban
    async def saved_navigate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle saved content navigation"""
        query = update.callback_query
        await query.answer()
        
        direction = query.data.split('_')[2]  # saved_nav_next or saved_nav_prev
        contents = context.user_data.get('contents', [])
        index = context.user_data.get('index', 0)
        
        if not contents:
            await query.answer("❌ No saved content available.", show_alert=True)
            return
        
        if direction == 'next' and index < len(contents) - 1:
            index += 1
        elif direction == 'prev' and index > 0:
            index -= 1
        else:
            await query.answer("⚠️ No more items in this direction.", show_alert=True)
            return
        
        context.user_data['index'] = index
        content = contents[index]
        
        # Build caption
        caption = f"💾 Saved Content\n\n📌 {content['title']}\n\n"
        caption += f"📂 {content['category'].title()}\n"
        caption += f"🔗 {content['platform'].upper()}\n"
        if content.get('description'):
            caption += f"📝 {content['description'][:150]}...\n\n"
        caption += f"🌐 {content['url']}\n\n"
        caption += f"📊 {index + 1}/{len(contents)}"
        
        # Navigation buttons
        keyboard = []
        nav_row = []
        if index > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data="saved_nav_prev"))
        if index < len(contents) - 1:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data="saved_nav_next"))
        if nav_row:
            keyboard.append(nav_row)
        keyboard.append([InlineKeyboardButton("« Back to Menu", callback_data="start")])
        
        try:
            # Delete old message and send new one
            await query.message.delete()
            if content.get('thumbnail'):
                await query.message.chat.send_photo(
                    photo=content['thumbnail'],
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.message.chat.send_message(
                    text=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            import logging
            logging.error(f"Saved navigation error: {e}")
            await query.answer("❌ Error loading content.", show_alert=True)

    @check_ban
    async def apply_time_filter(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Apply time filter to current content"""
        from database import Content
        from datetime import datetime, timezone, timedelta
        
        query = update.callback_query
        await query.answer()
        
        # Get filter from callback data
        time_filter = query.data.replace('filter_', '')  # 24h, 48h, week
        
        # Get current category from context
        category = context.user_data.get('category')
        subcategory = context.user_data.get('subcategory')
        league = context.user_data.get('league')
        
        if not category:
            await query.answer("❌ No category selected. Browse categories first.", show_alert=True)
            return
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            # Calculate time cutoff based on filter
            if time_filter == '24h':
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                filter_name = "Last 24 Hours"
            elif time_filter == 'week':
                cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                filter_name = "Last Week"
            else:  # Default 48h
                cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
                filter_name = "Last 48 Hours"
            
            limit = 20 if db_user.is_premium else 10
            
            # Query based on category type
            if subcategory:
                # Tech subcategory
                keywords = self.bot.tech_keywords.get(subcategory, [])
                all_contents = db.query(Content).filter(
                    Content.category == 'tech',
                    Content.created_at >= cutoff,
                    Content.thumbnail.isnot(None)
                ).order_by(Content.trend_score.desc()).limit(200).all()
                
                # Filter by keywords
                contents = []
                for c in all_contents:
                    text = f"{c.title} {c.description or ''}".lower()
                    match_score = sum(1 for kw in keywords if kw.lower() in text)
                    if match_score > 0:
                        contents.append({
                            'id': c.id, 'title': c.title, 'url': c.url,
                            'platform': c.platform, 'category': c.category,
                            'thumbnail': c.thumbnail, 'description': c.description,
                            'trend_score': c.trend_score
                        })
                contents = contents[:limit]
                
            elif league:
                # Sports league
                keywords = self.bot.sports_keywords.get(league, [])
                all_contents = db.query(Content).filter(
                    Content.category == 'sports',
                    Content.created_at >= cutoff,
                    Content.thumbnail.isnot(None)
                ).order_by(Content.trend_score.desc()).limit(200).all()
                
                # Filter by keywords
                contents = []
                for c in all_contents:
                    if league == 'all_sports':
                        contents.append({
                            'id': c.id, 'title': c.title, 'url': c.url,
                            'platform': c.platform, 'category': c.category,
                            'thumbnail': c.thumbnail, 'description': c.description,
                            'trend_score': c.trend_score
                        })
                    else:
                        text = f"{c.title} {c.description or ''}".lower()
                        match_score = sum(1 for kw in keywords if kw.lower() in text)
                        if match_score > 0:
                            contents.append({
                                'id': c.id, 'title': c.title, 'url': c.url,
                                'platform': c.platform, 'category': c.category,
                                'thumbnail': c.thumbnail, 'description': c.description,
                                'trend_score': c.trend_score
                            })
                contents = contents[:limit]
                
            else:
                # Regular category
                db_contents = db.query(Content).filter(
                    Content.category == category,
                    Content.created_at >= cutoff,
                    Content.thumbnail.isnot(None)
                ).order_by(Content.trend_score.desc()).limit(limit).all()
                
                contents = [{
                    'id': c.id, 'title': c.title, 'url': c.url,
                    'platform': c.platform, 'category': c.category,
                    'thumbnail': c.thumbnail, 'description': c.description,
                    'trend_score': c.trend_score
                } for c in db_contents]
            
            if not contents:
                await query.answer(f"❌ No content found for {filter_name}", show_alert=True)
                return
            
            # Update context with filtered results
            context.user_data['contents'] = contents
            context.user_data['index'] = 0
            context.user_data['time_filter'] = time_filter
            
            # Show success message
            await query.answer(f"✅ Filtered: {filter_name} ({len(contents)} items)", show_alert=True)
            
            # Send first filtered content
            await self.send_content(query, contents[0], 0, len(contents), db_user.is_premium)
            
        except Exception as e:
            import logging
            logging.error(f"Time filter error: {e}")
            await query.answer("❌ Error applying filter. Try again.", show_alert=True)
        finally:
            db.close()
