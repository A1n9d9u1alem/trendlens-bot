import os
import json
import redis
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy.orm import Session
from database import User, Content, UserInteraction, Payment, get_db, create_tables
from payment_handler import PaymentHandler
from dotenv import load_dotenv

load_dotenv()

class TrendLensBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_id = int(os.getenv('ADMIN_USER_ID', '0'))
        self.payment_handler = PaymentHandler()
        try:
            self.redis = redis.Redis.from_url(os.getenv('REDIS_URL'), ssl=True, ssl_cert_reqs=None)
        except:
            self.redis = None
        self.categories = ['memes', 'sports', 'tech', 'gaming', 'entertainment', 'news']
        
    def check_rate_limit(self, db_user):
        """Check if user exceeded rate limit"""
        if db_user.is_premium:
            return True
        
        # Check if columns exist
        if not hasattr(db_user, 'last_request') or not hasattr(db_user, 'request_count'):
            return True  # Skip rate limiting if columns don't exist
        
        now = datetime.utcnow()
        if db_user.last_request:
            time_diff = (now - db_user.last_request).total_seconds()
            if time_diff > 86400:  # Reset daily
                db_user.request_count = 0
        
        if db_user.request_count >= 10:  # Free tier limit
            return False
        
        db_user.request_count += 1
        db_user.last_request = now
        return True
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db = next(get_db())
        
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        if not db_user:
            db_user = User(telegram_id=user.id, username=user.username, categories=json.dumps([]))
            db.add(db_user)
            db.commit()
            
            # Notify admin of new user
            if self.admin_id:
                try:
                    await context.bot.send_message(
                        chat_id=self.admin_id,
                        text=f"🆕 New User\n\n👤 @{user.username or user.first_name}\n🆔 ID: {user.id}"
                    )
                except:
                    pass
        
        # Check if banned (if column exists)
        if hasattr(db_user, 'is_banned') and db_user.is_banned:
            await update.message.reply_text("⛔ You have been banned from using this bot.")
            return
        
        # Update last activity
        db_user.created_at = datetime.utcnow()
        db.commit()
        
        keyboard = [
            [InlineKeyboardButton("📂 Browse Categories", callback_data="categories")],
            [InlineKeyboardButton("⭐ Upgrade to Pro", callback_data="subscribe")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
        
        text = (f"🔥 Welcome to TrendLens AI!\n\n"
                f"Your hub for trending content from Reddit, YouTube, Twitter, and more.\n\n"
                f"Status: {'✨ Pro' if db_user.is_premium else '🆓 Free'}\n"
                f"Choose an option below:")
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        keyboard = [[InlineKeyboardButton(f"📁 {cat.title()}", callback_data=f"cat_{cat}")] 
                    for cat in self.categories]
        keyboard.append([InlineKeyboardButton("« Back", callback_data="start")])
        
        await query.edit_message_text(
            "Select a category to view trending content:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        category = query.data.split('_')[1]
        user = query.from_user
        db = next(get_db())
        
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        # Check if banned (if column exists)
        if hasattr(db_user, 'is_banned') and db_user.is_banned:
            await query.answer("⛔ You are banned", show_alert=True)
            return
        
        # Check rate limit
        if not self.check_rate_limit(db_user):
            db.commit()
            await query.answer("⚠️ Daily limit reached! Upgrade to Pro for unlimited access.", show_alert=True)
            return
        
        db.commit()
        limit = 20 if db_user.is_premium else 5
        
        # Trigger on-demand fetch for hot categories
        if category in ['sports', 'news']:
            try:
                requests.get(f'http://localhost:3000/fetch/{category}', timeout=2)
            except:
                pass
        
        # Get from cache first
        cached = []
        if self.redis:
            try:
                cached = self.redis.zrevrange(f"trending:{category}", 0, limit-1)
            except:
                cached = []
        
        if not cached:
            # Fallback to database
            contents = db.query(Content).filter(
                Content.category == category
            ).order_by(Content.trend_score.desc()).limit(limit).all()
        else:
            contents = [json.loads(c) for c in cached]
        
        if not contents:
            await query.edit_message_text(
                f"No trending content found for {category}.\n\nTry again later!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="categories")]])
            )
            return
        
        # Show first item
        context.user_data['category'] = category
        context.user_data['contents'] = contents
        context.user_data['index'] = 0
        
        await self.send_content(query, contents[0], 0, len(contents), db_user.is_premium)
    
    async def send_content(self, query, content, index, total, is_premium):
        if isinstance(content, dict):
            title = content['title']
            url = content['url']
            platform = content['platform']
            thumbnail = content.get('thumbnail')
            description = content.get('description', '')
        else:
            title = content.title
            url = content.url
            platform = content.platform
            thumbnail = content.thumbnail
            description = content.description or ''
        
        text = f"🔥 {title}\n\n"
        text += f"📱 Platform: {platform.upper()}\n"
        if is_premium and description:
            text += f"📝 {description[:150]}...\n\n"
        text += f"🔗 {url}\n\n"
        text += f"📊 Item {index+1}/{total}"
        
        keyboard = []
        nav_row = []
        if index > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"nav_prev"))
        if index < total - 1:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"nav_next"))
        if nav_row:
            keyboard.append(nav_row)
        
        keyboard.append([
            InlineKeyboardButton("💾 Save", callback_data=f"save_{index}"),
            InlineKeyboardButton("🔗 Open", url=url)
        ])
        keyboard.append([InlineKeyboardButton("« Categories", callback_data="categories")])
        
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            try:
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
    
    async def navigate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        direction = query.data.split('_')[1]
        contents = context.user_data.get('contents', [])
        index = context.user_data.get('index', 0)
        
        if direction == 'next' and index < len(contents) - 1:
            index += 1
        elif direction == 'prev' and index > 0:
            index -= 1
        
        context.user_data['index'] = index
        
        user = query.from_user
        db = next(get_db())
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        await self.send_content(query, contents[index], index, len(contents), db_user.is_premium)
    
    async def subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = next(get_db())
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if db_user.is_premium and db_user.subscription_end and db_user.subscription_end > datetime.utcnow():
            days_left = (db_user.subscription_end - datetime.utcnow()).days
            await query.edit_message_text(
                f"✅ You're already a Pro member!\n\n"
                f"⏰ {days_left} days remaining\n\n"
                f"Expires: {db_user.subscription_end.strftime('%Y-%m-%d')}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="start")]])
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("💳 View Payment Methods", callback_data="show_payment")],
            [InlineKeyboardButton("« Back", callback_data="start")]
        ]
        
        await query.edit_message_text(
            "⭐ TrendLens Pro Features:\n\n"
            "✅ Unlimited requests\n"
            "✅ All categories\n"
            "✅ Rich media previews\n"
            "✅ Advanced filters\n"
            "✅ Real-time updates\n"
            "✅ Ad-free experience\n"
            "✅ Save & bookmark content\n\n"
            "💰 Price: 300 ETB / $5 USD (30 days)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = next(get_db())
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        self.payment_handler.create_payment_request(db_user.id, 5.0, db)
        
        await query.edit_message_text(
            self.payment_handler.get_payment_message(),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="subscribe")]])
        )
    
    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide payment reference\n\n"
                "Usage: /confirm <reference>\n"
                "Example: /confirm TX123456789"
            )
            return
        
        reference = ' '.join(context.args)
        db = next(get_db())
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if self.payment_handler.confirm_payment(db_user.id, reference, db):
            await update.message.reply_text(
                "✅ Payment confirmation submitted!\n\n"
                f"📝 Reference: {reference}\n\n"
                "⏳ Your payment is being verified\n"
                "You'll be notified once approved (usually within 24 hours)"
            )
            
            if self.admin_id:
                try:
                    await context.bot.send_message(
                        chat_id=self.admin_id,
                        text=f"💰 New Payment Confirmation\n\n"
                             f"👤 User: @{user.username or user.first_name}\n"
                             f"🆔 ID: {user.id}\n"
                             f"📝 Reference: {reference}\n\n"
                             f"Approve: /approve {user.id} 30\n"
                             f"Reject: /reject {user.id}"
                    )
                except:
                    pass
        else:
            await update.message.reply_text(
                "❌ No pending payment found\n\n"
                "Please use /subscribe first to view payment details"
            )
    
    async def account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db = next(get_db())
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if db_user.is_premium and db_user.subscription_end and db_user.subscription_end > datetime.utcnow():
            days_left = (db_user.subscription_end - datetime.utcnow()).days
            status = f"✨ Pro Member\n⏰ {days_left} days remaining\n📅 Expires: {db_user.subscription_end.strftime('%Y-%m-%d')}"
        else:
            status = "🆓 Free Tier\n\nUpgrade to Pro: /subscribe"
        
        await update.message.reply_text(
            f"👤 Account Status\n\n"
            f"🆔 User ID: {user.id}\n"
            f"👤 Username: @{user.username or user.first_name}\n\n"
            f"{status}"
        )
    
    async def approve_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /approve <user_id> <days>\n"
                "Example: /approve 123456789 30"
            )
            return
        
        try:
            user_id = int(context.args[0])
            days = int(context.args[1])
        except:
            await update.message.reply_text("❌ Invalid user ID or days")
            return
        
        db = next(get_db())
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            await update.message.reply_text("❌ User not found")
            return
        
        if self.payment_handler.approve_payment(user.id, days, db):
            await update.message.reply_text(
                f"✅ Payment approved!\n\n"
                f"👤 User: @{user.username}\n"
                f"⏰ Pro activated for {days} days"
            )
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 Payment Confirmed!\n\n"
                         f"✅ Your Pro subscription is now active\n"
                         f"⏰ Duration: {days} days\n\n"
                         f"Enjoy unlimited access to all features!"
                )
            except:
                pass
        else:
            await update.message.reply_text("❌ Failed to approve payment")
    
    async def reject_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: /reject <user_id>\n"
                "Example: /reject 123456789"
            )
            return
        
        try:
            user_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Invalid user ID")
            return
        
        db = next(get_db())
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            await update.message.reply_text("❌ User not found")
            return
        
        if self.payment_handler.reject_payment(user.id, db):
            await update.message.reply_text(
                f"❌ Payment rejected\n\n"
                f"👤 User: @{user.username}"
            )
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ Payment Verification Failed\n\n"
                         f"Your payment could not be verified.\n"
                         f"Please contact support or try again."
                )
            except:
                pass
        else:
            await update.message.reply_text("❌ No pending payment found")
    
    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        db = next(get_db())
        
        total_users = db.query(User).count()
        pro_users = db.query(User).filter(User.is_premium == True).count()
        free_users = total_users - pro_users
        pending_payments = db.query(Payment).filter(Payment.status == 'submitted').count()
        approved_payments = db.query(Payment).filter(Payment.status == 'approved').count()
        rejected_payments = db.query(Payment).filter(Payment.status == 'rejected').count()
        
        # Active users (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_users = db.query(User).filter(User.created_at >= week_ago).count()
        
        # New users today
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
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
    
    async def revoke_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: /revoke <user_id>\n"
                "Example: /revoke 123456789"
            )
            return
        
        try:
            user_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Invalid user ID")
            return
        
        db = next(get_db())
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            await update.message.reply_text("❌ User not found")
            return
        
        user.is_premium = False
        user.subscription_end = None
        db.commit()
        
        await update.message.reply_text(
            f"✅ Pro access revoked\n\n"
            f"👤 User: @{user.username}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ Your Pro subscription has been revoked.\n\nContact support for more information."
            )
        except:
            pass
    
    async def list_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        db = next(get_db())
        
        # Get filter from args
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
    
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: /broadcast <message>\n"
                "Example: /broadcast New features coming soon!"
            )
            return
        
        message = ' '.join(context.args)
        db = next(get_db())
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
            except:
                failed += 1
        
        await update.message.reply_text(
            f"✅ Broadcast complete\n\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}"
        )
    
    async def grant_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /grant <user_id> <days>\n"
                "Example: /grant 123456789 30"
            )
            return
        
        try:
            user_id = int(context.args[0])
            days = int(context.args[1])
        except:
            await update.message.reply_text("❌ Invalid parameters")
            return
        
        db = next(get_db())
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            await update.message.reply_text("❌ User not found")
            return
        
        user.is_premium = True
        if user.subscription_end and user.subscription_end > datetime.utcnow():
            user.subscription_end += timedelta(days=days)
        else:
            user.subscription_end = datetime.utcnow() + timedelta(days=days)
        db.commit()
        
        await update.message.reply_text(
            f"✅ Pro granted!\n\n"
            f"👤 User: @{user.username}\n"
            f"⏰ Duration: {days} days"
        )
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎁 You've been granted Pro access!\n\n⏰ Duration: {days} days\n\nEnjoy!"
            )
        except:
            pass
    
    async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: /ban <user_id>\n"
                "Example: /ban 123456789"
            )
            return
        
        try:
            user_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Invalid user ID")
            return
        
        db = next(get_db())
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            await update.message.reply_text("❌ User not found")
            return
        
        if hasattr(user, 'is_banned'):
            user.is_banned = True
        else:
            await update.message.reply_text("⚠️ Ban feature not available. Run database migration first.")
            return
        db.commit()
        
        await update.message.reply_text(
            f"⛔ User banned\n\n"
            f"👤 @{user.username}\n"
            f"🆔 ID: {user_id}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="⛔ You have been banned from using this bot for violating terms of service."
            )
        except:
            pass
    
    async def unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: /unban <user_id>\n"
                "Example: /unban 123456789"
            )
            return
        
        try:
            user_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Invalid user ID")
            return
        
        db = next(get_db())
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            await update.message.reply_text("❌ User not found")
            return
        
        if hasattr(user, 'is_banned'):
            user.is_banned = False
        else:
            await update.message.reply_text("⚠️ Unban feature not available. Run database migration first.")
            return
        db.commit()
        
        await update.message.reply_text(
            f"✅ User unbanned\n\n"
            f"👤 @{user.username}\n"
            f"🆔 ID: {user_id}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ You have been unbanned. You can now use the bot again."
            )
        except:
            pass
    
    async def trending(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        category = context.args[0] if context.args else 'memes'
        
        if category not in self.categories:
            await update.message.reply_text(f"Invalid category. Choose from: {', '.join(self.categories)}")
            return
        
        user = update.effective_user
        db = next(get_db())
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        limit = 20 if db_user.is_premium else 5
        cached = []
        if self.redis:
            try:
                cached = self.redis.zrevrange(f"trending:{category}", 0, limit-1)
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
    
    async def save_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        
        user = query.from_user
        db = next(get_db())
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
                    content_url = content.get('url', '')
                    content_title = content.get('title', '')
                else:
                    content_url = content.url
                    content_title = content.title
                    
                    interaction = UserInteraction(
                        user_id=db_user.id,
                        content_id=content.id,
                        action='save'
                    )
                    db.add(interaction)
                    db.commit()
                
                await query.answer("✅ Saved!", show_alert=True)
            else:
                await query.answer("❌ Not found", show_alert=True)
        except Exception as e:
            await query.answer("✅ Saved!", show_alert=True)
    
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📂 My Topics", callback_data="mytopics")],
            [InlineKeyboardButton("🔔 Notifications", callback_data="notifications")],
            [InlineKeyboardButton("« Back", callback_data="start")]
        ]
        
        await query.edit_message_text(
            "⚙️ Settings\n\nManage your preferences:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    def run(self):
        app = Application.builder().token(self.token).build()
        
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("trending", self.trending))
        app.add_handler(CommandHandler("confirm", self.confirm_payment))
        app.add_handler(CommandHandler("account", self.account))
        app.add_handler(CommandHandler("approve", self.approve_payment))
        app.add_handler(CommandHandler("reject", self.reject_payment))
        app.add_handler(CommandHandler("stats", self.admin_stats))
        app.add_handler(CommandHandler("revoke", self.revoke_pro))
        app.add_handler(CommandHandler("users", self.list_users))
        app.add_handler(CommandHandler("broadcast", self.broadcast))
        app.add_handler(CommandHandler("grant", self.grant_pro))
        app.add_handler(CallbackQueryHandler(self.show_categories, pattern="^categories$"))
        app.add_handler(CallbackQueryHandler(self.show_category, pattern="^cat_"))
        app.add_handler(CallbackQueryHandler(self.navigate, pattern="^nav_"))
        app.add_handler(CallbackQueryHandler(self.save_content, pattern="^save_"))
        app.add_handler(CallbackQueryHandler(self.subscribe, pattern="^subscribe$"))
        app.add_handler(CallbackQueryHandler(self.show_payment, pattern="^show_payment$"))
        app.add_handler(CallbackQueryHandler(self.settings, pattern="^settings$"))
        app.add_handler(CallbackQueryHandler(self.start, pattern="^start$"))
        
        print("🤖 TrendLens AI Bot started!")
        print(f"👤 Admin ID: {self.admin_id}")
        app.run_polling()

if __name__ == '__main__':
    bot = TrendLensBot()
    bot.run()