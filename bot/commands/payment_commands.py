"""
Payment Commands Module
Handles subscription and payment commands
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal, User
from datetime import datetime, timezone
from ban_decorator import check_ban


class PaymentCommands:
    """Payment command handlers"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    @check_ban
    async def subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command - show subscription info"""
        query = update.callback_query if update.callback_query else None
        message = update.message if update.message else None
        
        user = update.effective_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if hasattr(db_user, 'is_banned') and db_user.is_banned:
                text = "⛔ You have been banned from using this bot."
                if query:
                    await query.edit_message_text(text)
                else:
                    await message.reply_text(text)
                return
            
            if db_user.is_premium and db_user.subscription_end:
                sub_end = db_user.subscription_end
                if sub_end.tzinfo is None:
                    sub_end = sub_end.replace(tzinfo=timezone.utc)
                
                if sub_end > datetime.now(timezone.utc):
                    days_left = (sub_end - datetime.now(timezone.utc)).days
                    text = (
                        f"✅ You're already a Pro member!\n\n"
                        f"⏰ {days_left} days remaining\n\n"
                        f"Expires: {sub_end.strftime('%Y-%m-%d')}"
                    )
                    keyboard = [[InlineKeyboardButton("« Back", callback_data="start")]]
                    
                    if query:
                        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
                    else:
                        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
                    return
            
            keyboard = [
                [InlineKeyboardButton("💳 View Payment Methods", callback_data="show_payment")],
                [InlineKeyboardButton("« Back", callback_data="start")]
            ]
            
            text = (
                "⭐ TrendLens Pro Features:\n\n"
                "✅ Unlimited requests\n"
                "✅ All categories\n"
                "✅ Rich media previews\n"
                "✅ Advanced filters\n"
                "✅ Real-time updates\n"
                "✅ Ad-free experience\n"
                "✅ Save & bookmark content\n\n"
                "💰 Price: 300 ETB / $5 USD (30 days)"
            )
            
            if query:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        finally:
            db.close()
    
    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /confirm command"""
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide payment reference\n\n"
                "Usage: /confirm <reference>\n"
                "Example: /confirm TX123456789"
            )
            return
        
        reference = self.bot.sanitize_input(' '.join(context.args), max_length=100)
        
        if not self.bot.validate_payment_reference(reference):
            await update.message.reply_text(
                "❌ Invalid payment reference format\n\n"
                "Reference must be 5-100 characters (letters, numbers, dash, underscore only)\n"
                "Example: TX123456789 or PAY-2024-001"
            )
            return
        
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ User not found. Use /start first.")
                return
            
            if self.bot.payment_handler.confirm_payment(db_user.id, reference, db):
                await update.message.reply_text(
                    "✅ Payment confirmation submitted!\n\n"
                    f"📝 Reference: {reference}\n\n"
                    "⏳ Your payment is being verified\n"
                    "You'll be notified once approved (usually within 24 hours)"
                )
                
                if self.bot.admin_id:
                    try:
                        await context.bot.send_message(
                            chat_id=self.bot.admin_id,
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
        finally:
            db.close()
    
    async def approve_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /approve command (admin only)"""
        if update.effective_user.id != self.bot.admin_id:
            return
        
        if not self.bot.check_admin_rate_limit(update.effective_user.id, 'approve', max_per_minute=5):
            await update.message.reply_text("⚠️ Rate limit exceeded. Wait a minute.")
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
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            
            if not user:
                await update.message.reply_text("❌ User not found")
                return
            
            if self.bot.payment_handler.approve_payment(user.id, days, db):
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
        finally:
            db.close()
    
    async def reject_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reject command (admin only)"""
        if update.effective_user.id != self.bot.admin_id:
            return
        
        if not self.bot.check_admin_rate_limit(update.effective_user.id, 'reject', max_per_minute=5):
            await update.message.reply_text("⚠️ Rate limit exceeded. Wait a minute.")
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
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            
            if not user:
                await update.message.reply_text("❌ User not found")
                return
            
            if self.bot.payment_handler.reject_payment(user.id, db):
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
        finally:
            db.close()
