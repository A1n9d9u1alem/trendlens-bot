"""
Content Moderation Module
Handles content approval and rejection for quality control
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal, Content
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ContentModeration:
    """Content moderation command handlers"""
    
    def __init__(self, bot_instance: 'TrendLensBot') -> None:
        self.bot = bot_instance
    
    def _is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id == self.bot.admin_id
    
    async def moderation_queue(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show content moderation queue"""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        db = SessionLocal()
        try:
            # Get pending content (low quality score or flagged)
            pending_contents = db.query(Content).filter(
                Content.trend_score < 50  # Low quality threshold
            ).order_by(Content.created_at.desc()).limit(20).all()
            
            if not pending_contents:
                await update.message.reply_text(
                    "✅ No content pending moderation!\n\n"
                    "All content meets quality standards."
                )
                return
            
            # Store in context
            context.user_data['moderation_queue'] = [
                {
                    'id': c.id,
                    'title': c.title,
                    'url': c.url,
                    'platform': c.platform,
                    'category': c.category,
                    'thumbnail': c.thumbnail,
                    'description': c.description,
                    'trend_score': c.trend_score,
                    'created_at': c.created_at
                }
                for c in pending_contents
            ]
            context.user_data['moderation_index'] = 0
            
            await update.message.reply_text(
                f"📋 Moderation Queue\n\n"
                f"Found {len(pending_contents)} items for review\n\n"
                f"Reviewing content..."
            )
            
            # Show first item
            await self.show_moderation_item(
                update.message,
                context.user_data['moderation_queue'][0],
                0,
                len(pending_contents)
            )
            
        except Exception as e:
            logger.error(f"Moderation queue error: {e}")
            await update.message.reply_text("❌ Error loading moderation queue.")
        finally:
            db.close()
    
    async def show_moderation_item(
        self,
        message,
        content: dict,
        index: int,
        total: int
    ) -> None:
        """Show a content item for moderation"""
        title = content.get('title', 'No title')
        url = content.get('url', '')
        platform = content.get('platform', 'Unknown')
        category = content.get('category', 'Unknown')
        trend_score = content.get('trend_score', 0)
        thumbnail = content.get('thumbnail')
        description = content.get('description', '')
        created_at = content.get('created_at')
        
        # Build caption
        caption = f"📋 Moderation Review\n\n"
        caption += f"📊 Item {index + 1}/{total}\n\n"
        caption += f"📌 {title}\n\n"
        caption += f"📂 Category: {category.title()}\n"
        caption += f"🔗 Platform: {platform}\n"
        caption += f"📈 Trend Score: {trend_score}\n"
        
        if created_at:
            caption += f"📅 Posted: {created_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        if description:
            caption += f"\n📝 {description[:150]}...\n"
        
        caption += f"\n🌐 {url}\n\n"
        caption += "⚠️ Low quality score - Review needed"
        
        # Moderation buttons
        buttons = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"mod_approve_{content['id']}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"mod_reject_{content['id']}")
            ]
        ]
        
        # Navigation
        nav_row = []
        if index > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data="mod_nav_prev"))
        if index < total - 1:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data="mod_nav_next"))
        
        if nav_row:
            buttons.append(nav_row)
        
        buttons.append([InlineKeyboardButton("🚫 Exit Queue", callback_data="mod_exit")])
        
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
            logger.error(f"Error showing moderation item: {e}")
            await message.reply_text(
                caption,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    
    async def approve_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Approve content"""
        query = update.callback_query
        await query.answer()
        
        if not self._is_admin(query.from_user.id):
            await query.answer("⛔ Admin only!", show_alert=True)
            return
        
        try:
            # Get content ID from callback data
            content_id = int(query.data.split('_')[2])
            
            db = SessionLocal()
            try:
                content = db.query(Content).filter(Content.id == content_id).first()
                
                if not content:
                    await query.answer("❌ Content not found", show_alert=True)
                    return
                
                # Boost trend score to approve
                content.trend_score = max(content.trend_score, 75)  # Minimum approved score
                db.commit()
                
                await query.answer("✅ Content approved!", show_alert=True)
                
                # Move to next item
                await self.navigate_moderation(update, context, 'next')
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Approve content error: {e}")
            await query.answer("❌ Error approving content", show_alert=True)
    
    async def reject_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Reject content"""
        query = update.callback_query
        await query.answer()
        
        if not self._is_admin(query.from_user.id):
            await query.answer("⛔ Admin only!", show_alert=True)
            return
        
        try:
            # Get content ID from callback data
            content_id = int(query.data.split('_')[2])
            
            db = SessionLocal()
            try:
                content = db.query(Content).filter(Content.id == content_id).first()
                
                if not content:
                    await query.answer("❌ Content not found", show_alert=True)
                    return
                
                # Delete rejected content
                db.delete(content)
                db.commit()
                
                await query.answer("❌ Content rejected and removed!", show_alert=True)
                
                # Remove from queue and move to next
                queue = context.user_data.get('moderation_queue', [])
                queue = [item for item in queue if item['id'] != content_id]
                context.user_data['moderation_queue'] = queue
                
                if not queue:
                    await query.edit_message_text(
                        "✅ Moderation queue complete!\n\n"
                        "All items have been reviewed."
                    )
                    return
                
                # Show next item
                index = context.user_data.get('moderation_index', 0)
                if index >= len(queue):
                    index = len(queue) - 1
                context.user_data['moderation_index'] = index
                
                await query.message.delete()
                await self.show_moderation_item(
                    query.message,
                    queue[index],
                    index,
                    len(queue)
                )
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Reject content error: {e}")
            await query.answer("❌ Error rejecting content", show_alert=True)
    
    async def navigate_moderation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        direction: str = 'next'
    ) -> None:
        """Navigate moderation queue"""
        query = update.callback_query
        
        queue = context.user_data.get('moderation_queue', [])
        index = context.user_data.get('moderation_index', 0)
        
        if not queue:
            await query.answer("❌ No items in queue", show_alert=True)
            return
        
        # Navigate
        if direction == 'next' and index < len(queue) - 1:
            index += 1
        elif direction == 'prev' and index > 0:
            index -= 1
        else:
            if direction == 'next':
                await query.edit_message_text(
                    "✅ Moderation queue complete!\n\n"
                    "All items have been reviewed.\n\n"
                    "Use /moderation_queue to review more content."
                )
            return
        
        context.user_data['moderation_index'] = index
        
        # Show item
        try:
            await query.message.delete()
            await self.show_moderation_item(
                query.message,
                queue[index],
                index,
                len(queue)
            )
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            await query.answer("❌ Error loading item", show_alert=True)
    
    async def mod_navigate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle moderation navigation callback"""
        query = update.callback_query
        await query.answer()
        
        direction = query.data.split('_')[2]  # mod_nav_prev or mod_nav_next
        await self.navigate_moderation(update, context, direction)
    
    async def mod_exit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Exit moderation queue"""
        query = update.callback_query
        await query.answer()
        
        try:
            await query.edit_message_text(
                "🚫 Exited moderation queue\n\n"
                "Use /moderation_queue to resume reviewing content."
            )
        except:
            pass
        
        # Clear context
        context.user_data.pop('moderation_queue', None)
        context.user_data.pop('moderation_index', None)
    
    async def content_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show content quality statistics"""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        db = SessionLocal()
        try:
            # Get statistics
            total_content = db.query(Content).count()
            high_quality = db.query(Content).filter(Content.trend_score >= 75).count()
            medium_quality = db.query(Content).filter(
                Content.trend_score >= 50,
                Content.trend_score < 75
            ).count()
            low_quality = db.query(Content).filter(Content.trend_score < 50).count()
            
            # Calculate percentages
            high_pct = (high_quality / total_content * 100) if total_content > 0 else 0
            medium_pct = (medium_quality / total_content * 100) if total_content > 0 else 0
            low_pct = (low_quality / total_content * 100) if total_content > 0 else 0
            
            text = (
                f"📊 Content Quality Statistics\n\n"
                f"📈 Total Content: {total_content}\n\n"
                f"✅ High Quality (75+): {high_quality} ({high_pct:.1f}%)\n"
                f"⚠️ Medium Quality (50-74): {medium_quality} ({medium_pct:.1f}%)\n"
                f"❌ Low Quality (<50): {low_quality} ({low_pct:.1f}%)\n\n"
                f"💡 Review low quality content:\n"
                f"/moderation_queue"
            )
            
            await update.message.reply_text(text)
            
        except Exception as e:
            logger.error(f"Content stats error: {e}")
            await update.message.reply_text("❌ Error loading statistics.")
        finally:
            db.close()
