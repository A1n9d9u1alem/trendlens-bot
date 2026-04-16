"""
Admin Commands Module
Handles all admin-only commands
"""

from telegram import Update
from telegram.ext import ContextTypes
from database import SessionLocal, User, Payment, Analytics, Content
from datetime import datetime, timedelta, timezone
import asyncio


class AdminCommands:
    """Admin command handlers"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id == self.bot.admin_id
    
    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        if not self.is_admin(update.effective_user.id):
            return
        
        db = SessionLocal()
        try:
            total_users = db.query(User).count()
            pro_users = db.query(User).filter(User.is_premium == True).count()
            free_users = total_users - pro_users
            pending_payments = db.query(Payment).filter(Payment.status == 'submitted').count()
            approved_payments = db.query(Payment).filter(Payment.status == 'approved').count()
            rejected_payments = db.query(Payment).filter(Payment.status == 'rejected').count()
            
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            active_users = db.query(User).filter(User.created_at >= week_ago).count()
            
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            new_today = db.query(User).filter(User.created_at >= today).count()
            
            await update.message.reply_text(
                f"📊 TrendLens AI Statistics\n\n"
                f"👥 Total Users: {total_users}\n"
                f"🆓 Free Users: {free_users}\n"
                f"✨ Pro Users: {pro_users}\n"
                f"🔥 Active (7d): {active_users}\n"
                f"🆕 New Today: {new_today}\n\n"
                f"💰 Payments:\n"
                f"⏳ Pending: {pending_payments}\n"
                f"✅ Approved: {approved_payments}\n"
                f"❌ Rejected: {rejected_payments}\n\n"
                f"💵 Revenue: ${approved_payments * 5}\n\n"
                f"Conversion: {(pro_users/total_users*100):.1f}%"
            )
        finally:
            db.close()
    
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command"""
        if not self.is_admin(update.effective_user.id):
            return
        
        if not self.bot.check_admin_rate_limit(update.effective_user.id, 'broadcast', max_per_minute=2):
            await update.message.reply_text("⚠️ Rate limit exceeded. Wait a minute.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: /broadcast <message>\n"
                "Example: /broadcast New features coming soon!"
            )
            return
        
        message = self.bot.sanitize_input(' '.join(context.args), max_length=4000)
        if len(message) < 1:
            await update.message.reply_text("❌ Message cannot be empty")
            return
        
        db = SessionLocal()
        try:
            users = db.query(User).all()
            
            sent = 0
            failed = 0
            
            await update.message.reply_text(f"📡 Broadcasting to {len(users)} users...")
            
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"📢 Announcement\n\n{message}"
                    )
                    sent += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    failed += 1
            
            await update.message.reply_text(
                f"✅ Broadcast complete\n\n"
                f"✅ Sent: {sent}\n"
                f"❌ Failed: {failed}"
            )
        finally:
            db.close()
    
    async def list_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /users command"""
        if not self.is_admin(update.effective_user.id):
            return
        
        db = SessionLocal()
        try:
            filter_type = context.args[0] if context.args else 'all'
            
            if filter_type == 'pro':
                users = db.query(User).filter(User.is_premium == True).order_by(User.created_at.desc()).limit(20).all()
                title = "✨ Pro Users (Last 20)"
            elif filter_type == 'pending':
                pending = db.query(Payment).filter(Payment.status == 'submitted').order_by(Payment.created_at.desc()).limit(20).all()
                text = f"⏳ Pending Payments ({len(pending)})\n\n"
                for p in pending:
                    user = db.query(User).filter(User.id == p.user_id).first()
                    text += f"@{user.username} - {user.telegram_id}\n📝 {p.reference}\n\n"
                await update.message.reply_text(text or "No pending payments")
                return
            else:
                users = db.query(User).order_by(User.created_at.desc()).limit(20).all()
                title = "👥 Recent Users (Last 20)"
            
            text = f"{title}\n\n"
            for u in users:
                status = "✨" if u.is_premium else "🆓"
                text += f"{status} @{u.username or 'No username'} - {u.telegram_id}\n"
            
            await update.message.reply_text(text)
        finally:
            db.close()
    
    async def bulk_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /bulk_stats command"""
        if not self.is_admin(update.effective_user.id):
            return
        
        from bulk_operations import get_bulk_ops
        bulk_ops = get_bulk_ops()
        
        try:
            stats = bulk_ops.get_bulk_statistics()
            
            text = f"📊 Bulk Operations Statistics\n\n"
            text += f"👥 Total Users: {stats['total_users']}\n"
            text += f"✨ Pro Users: {stats['pro_users']}\n"
            text += f"🆓 Free Users: {stats['free_users']}\n"
            text += f"🔥 Active (7d): {stats['active_users_7d']}\n"
            text += f"⚠️ Expiring Soon: {stats['expiring_soon']}\n"
            text += f"💤 Inactive (30d): {stats['inactive_30d']}\n"
            text += f"📈 Conversion: {stats['conversion_rate']}\n\n"
            text += f"Commands:\n"
            text += f"/bulk_grant - Grant pro to multiple users\n"
            text += f"/bulk_revoke - Revoke pro from users\n"
            text += f"/bulk_message - Message multiple users\n"
            text += f"/message_inactive - Message inactive users\n"
            text += f"/export_users - Export users to CSV"
            
            await update.message.reply_text(text)
        finally:
            bulk_ops.close()

    async def analytics_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Generate advanced analytics report"""
        if update.effective_user.id != self.bot.admin_id:
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        from bot.services.advanced_analytics import AdvancedAnalytics
        
        await update.message.reply_text("📊 Generating analytics report...")
        
        try:
            # Get trending categories
            trending = AdvancedAnalytics.get_trending_categories()
            
            report = "📊 Advanced Analytics Report\n\n"
            report += "🔥 Trending Categories (Last 24h):\n\n"
            
            for i, cat in enumerate(trending[:5], 1):
                report += f"{i}. {cat['category'].title()}\n"
                report += f"   👁️ Views: {cat['views']}\n"
                report += f"   📄 Content: {cat['content_count']}\n"
                report += f"   📈 Avg: {cat['avg_views_per_content']:.1f} views/content\n\n"
            
            await update.message.reply_text(report)
            
        except Exception as e:
            import logging
            logging.error(f"Analytics report error: {e}")
            await update.message.reply_text("❌ Error generating report.")
    
    async def recalculate_scores(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Recalculate all content scores"""
        if update.effective_user.id != self.bot.admin_id:
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        from bot.services.advanced_analytics import AdvancedAnalytics
        
        await update.message.reply_text("🔄 Recalculating all content scores...\n\nThis may take a moment.")
        
        try:
            updated, errors = AdvancedAnalytics.recalculate_all_scores()
            
            await update.message.reply_text(
                f"✅ Score Recalculation Complete!\n\n"
                f"📊 Updated: {updated} items\n"
                f"❌ Errors: {errors} items\n\n"
                f"All content now has fresh trending and quality scores."
            )
            
        except Exception as e:
            import logging
            logging.error(f"Recalculate scores error: {e}")
            await update.message.reply_text("❌ Error recalculating scores.")
    
    async def quality_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Generate quality analysis report"""
        if update.effective_user.id != self.bot.admin_id:
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        from bot.services.advanced_analytics import AdvancedAnalytics
        from database import SessionLocal, Content
        
        db = SessionLocal()
        try:
            # Sample content for quality analysis
            contents = db.query(Content).order_by(Content.created_at.desc()).limit(100).all()
            
            if not contents:
                await update.message.reply_text("❌ No content available for analysis.")
                return
            
            # Calculate quality scores
            quality_scores = []
            for content in contents:
                score = AdvancedAnalytics.calculate_quality_score(content)
                quality_scores.append(score)
            
            # Statistics
            avg_quality = sum(quality_scores) / len(quality_scores)
            high_quality = sum(1 for s in quality_scores if s >= 70)
            medium_quality = sum(1 for s in quality_scores if 40 <= s < 70)
            low_quality = sum(1 for s in quality_scores if s < 40)
            
            report = (
                f"📊 Quality Analysis Report\n\n"
                f"📈 Sample Size: {len(contents)} recent items\n\n"
                f"📊 Average Quality: {avg_quality:.1f}/100\n\n"
                f"✅ High Quality (70+): {high_quality} ({high_quality/len(contents)*100:.1f}%)\n"
                f"⚠️ Medium Quality (40-69): {medium_quality} ({medium_quality/len(contents)*100:.1f}%)\n"
                f"❌ Low Quality (<40): {low_quality} ({low_quality/len(contents)*100:.1f}%)\n\n"
                f"💡 Recommendation:\n"
            )
            
            if avg_quality >= 70:
                report += "Excellent! Content quality is high."
            elif avg_quality >= 50:
                report += "Good. Consider reviewing low-quality items."
            else:
                report += "Action needed. Review and improve content quality."
            
            await update.message.reply_text(report)
            
        except Exception as e:
            import logging
            logging.error(f"Quality report error: {e}")
            await update.message.reply_text("❌ Error generating quality report.")
        finally:
            db.close()

    async def realtime_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Check realtime updates status"""
        if update.effective_user.id != self.bot.admin_id:
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        status = self.bot.realtime_updates.get_status()
        
        text = "⚡ Realtime Updates Status\n\n"
        text += f"🔄 Running: {'✅ Yes' if status['running'] else '❌ No'}\n"
        text += f"⚽ Sports Updates: {'✅ Active' if status['sports_active'] else '❌ Inactive'}\n"
        text += f"📰 News Updates: {'✅ Active' if status['news_active'] else '❌ Inactive'}\n\n"
        text += f"⏱️ Sports Interval: {status['sports_interval']}s ({status['sports_interval']//60} min)\n"
        text += f"⏱️ News Interval: {status['news_interval']}s ({status['news_interval']//60} min)\n\n"
        text += "💡 Pro users receive live notifications"
        
        await update.message.reply_text(text)
    
    async def live_sports(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get live sports summary"""
        summary = await self.bot.realtime_updates.get_live_sports_summary()
        await update.message.reply_text(summary)
    
    async def breaking_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get breaking news summary"""
        summary = await self.bot.realtime_updates.get_breaking_news_summary()
        await update.message.reply_text(summary)

    async def db_pool_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Check database connection pool status"""
        if update.effective_user.id != self.bot.admin_id:
            await update.message.reply_text("⛔ Admin only command!")
            return
        
        from database import get_pool_status
        
        try:
            status = get_pool_status()
            
            # Calculate percentages
            pool_usage = (status['in_use'] / status['total_connections'] * 100) if status['total_connections'] > 0 else 0
            
            # Status indicator
            if pool_usage < 50:
                status_emoji = "✅"
                status_text = "Healthy"
            elif pool_usage < 80:
                status_emoji = "⚠️"
                status_text = "Moderate"
            else:
                status_emoji = "🔴"
                status_text = "High Load"
            
            text = (
                f"💾 Database Connection Pool Status\n\n"
                f"{status_emoji} Status: {status_text}\n\n"
                f"📊 Pool Configuration:\n"
                f"• Pool Size: {status['pool_size']}\n"
                f"• Max Overflow: {status['overflow']}\n"
                f"• Total Capacity: {status['total_connections']}\n\n"
                f"🔄 Current Usage:\n"
                f"• In Use: {status['in_use']}\n"
                f"• Available: {status['available']}\n"
                f"• Checked Out: {status['checked_out']}\n"
                f"• Checked In: {status['checked_in']}\n\n"
                f"📈 Usage: {pool_usage:.1f}%\n\n"
                f"💡 Tip: Keep usage below 80% for optimal performance"
            )
            
            await update.message.reply_text(text)
            
        except Exception as e:
            import logging
            logging.error(f"DB pool status error: {e}")
            await update.message.reply_text("❌ Error getting pool status.")
