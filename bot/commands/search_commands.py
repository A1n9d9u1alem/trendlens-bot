"""
Search Commands Module
Handles content search functionality
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal, User, Content
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SearchCommands:
    """Search command handlers"""
    
    def __init__(self, bot_instance: 'TrendLensBot') -> None:
        self.bot = bot_instance
    
    async def search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /search command"""
        if not context.args:
            await update.message.reply_text(
                "🔍 Search for trending content!\n\n"
                "Usage: /search <keyword>\n\n"
                "Examples:\n"
                "/search AI\n"
                "/search football\n"
                "/search memes\n"
                "/search python programming\n\n"
                "💡 Tip: Use specific keywords for better results"
            )
            return
        
        query = ' '.join(context.args)
        user = update.effective_user
        
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await update.message.reply_text("❌ User not found. Use /start first.")
                return
            
            # Search in database
            search_term = f"%{query.lower()}%"
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)  # Last 7 days
            
            # Search in title and description
            results = db.query(Content).filter(
                (Content.title.ilike(search_term)) | 
                (Content.description.ilike(search_term)),
                Content.created_at >= cutoff,
                Content.thumbnail.isnot(None)
            ).order_by(Content.trend_score.desc()).limit(50).all()
            
            if not results:
                await update.message.reply_text(
                    f"❌ No results found for '{query}'\n\n"
                    "💡 Try:\n"
                    "• Different keywords\n"
                    "• Broader search terms\n"
                    "• Check spelling\n\n"
                    "Browse categories: /start"
                )
                return
            
            # Store results in context
            context.user_data['search_query'] = query
            context.user_data['search_results'] = [
                {
                    'id': r.id,
                    'title': r.title,
                    'url': r.url,
                    'platform': r.platform,
                    'category': r.category,
                    'thumbnail': r.thumbnail,
                    'description': r.description,
                    'trend_score': r.trend_score
                }
                for r in results
            ]
            context.user_data['search_index'] = 0
            
            # Send first result
            await update.message.reply_text(
                f"🔍 Found {len(results)} results for '{query}'\n\n"
                f"Showing top results..."
            )
            
            await self.send_search_result(
                update.message,
                context.user_data['search_results'][0],
                0,
                len(results),
                db_user.is_premium,
                query
            )
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await update.message.reply_text(
                "❌ Search failed. Please try again.\n\n"
                "If the problem persists, contact support."
            )
        finally:
            db.close()
    
    async def send_search_result(
        self,
        message,
        content: Dict[str, Any],
        index: int,
        total: int,
        is_premium: bool,
        query: str
    ) -> None:
        """Send a search result with navigation"""
        title = content.get('title', 'No title')
        url = content.get('url', '')
        platform = content.get('platform', 'Unknown')
        category = content.get('category', 'Unknown')
        thumbnail = content.get('thumbnail')
        description = content.get('description', '')
        
        # Build caption
        caption = f"🔍 Search: '{query}'\n\n"
        caption += f"📊 Result {index + 1}/{total}\n\n"
        caption += f"📌 {title}\n\n"
        caption += f"📂 Category: {category.title()}\n"
        caption += f"🔗 Platform: {platform}\n"
        
        if description:
            caption += f"📝 {description[:100]}...\n\n"
        
        caption += f"🌐 {url}"
        
        # Navigation buttons
        buttons = []
        nav_row = []
        
        if index > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data="search_nav_prev"))
        if index < total - 1:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data="search_nav_next"))
        
        if nav_row:
            buttons.append(nav_row)
        
        # Save button for Pro users
        if is_premium:
            buttons.append([InlineKeyboardButton("💾 Save", callback_data=f"search_save_{index}")])
        
        # Action buttons
        buttons.append([
            InlineKeyboardButton("🔍 New Search", callback_data="new_search"),
            InlineKeyboardButton("📂 Categories", callback_data="categories")
        ])
        
        try:
            if thumbnail:
                await message.reply_photo(
                    photo=thumbnail,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                await message.reply_text(
                    caption,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
        except Exception as e:
            logger.error(f"Error sending search result: {e}")
            await message.reply_text(
                caption,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    
    async def search_navigate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle search result navigation"""
        query = update.callback_query
        await query.answer()
        
        direction = query.data.split('_')[2]  # search_nav_prev or search_nav_next
        results = context.user_data.get('search_results', [])
        index = context.user_data.get('search_index', 0)
        search_query = context.user_data.get('search_query', '')
        
        if not results:
            await query.answer("❌ No search results. Use /search <keyword>", show_alert=True)
            return
        
        # Navigate
        if direction == 'next' and index < len(results) - 1:
            index += 1
        elif direction == 'prev' and index > 0:
            index -= 1
        else:
            await query.answer("⚠️ No more results in this direction.", show_alert=True)
            return
        
        context.user_data['search_index'] = index
        
        # Get user
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            # Delete old message and send new result
            await query.message.delete()
            await self.send_search_result(
                query.message,
                results[index],
                index,
                len(results),
                db_user.is_premium,
                search_query
            )
        except Exception as e:
            logger.error(f"Search navigation error: {e}")
            await query.answer("❌ Error loading result. Try again.", show_alert=True)
        finally:
            db.close()
    
    async def search_save(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Save a search result"""
        from database import UserInteraction
        
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user.is_premium:
                await query.answer("⭐ Pro feature! Upgrade to save content.", show_alert=True)
                return
            
            # Get content index from callback data
            try:
                index = int(query.data.split('_')[2])
                results = context.user_data.get('search_results', [])
                
                if index < len(results):
                    content = results[index]
                    content_id = content.get('id')
                    
                    if content_id:
                        # Check if already saved
                        existing = db.query(UserInteraction).filter(
                            UserInteraction.user_id == db_user.id,
                            UserInteraction.content_id == content_id,
                            UserInteraction.action == 'save'
                        ).first()
                        
                        if not existing:
                            # Save content
                            interaction = UserInteraction(
                                user_id=db_user.id,
                                content_id=content_id,
                                action='save',
                                timestamp=datetime.now(timezone.utc)
                            )
                            db.add(interaction)
                            db.commit()
                            
                            await query.answer("✅ Saved!", show_alert=True)
                        else:
                            await query.answer("Already saved!", show_alert=True)
                    else:
                        await query.answer("❌ Cannot save", show_alert=True)
                else:
                    await query.answer("❌ Not found", show_alert=True)
            except Exception as e:
                logger.error(f"Error saving search result: {e}")
                await query.answer("❌ Error saving", show_alert=True)
        finally:
            db.close()
    
    async def new_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Prompt for new search"""
        query = update.callback_query
        await query.answer()
        
        try:
            await query.edit_message_text(
                "🔍 Start a new search!\n\n"
                "Use: /search <keyword>\n\n"
                "Examples:\n"
                "• /search AI technology\n"
                "• /search football highlights\n"
                "• /search funny memes\n\n"
                "💡 Be specific for better results!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📂 Browse Categories", callback_data="categories")
                ]])
            )
        except:
            pass
