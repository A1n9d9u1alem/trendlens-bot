from functools import wraps
from database import SessionLocal
from sqlalchemy import text
import time

# Cache banned users for 60 seconds to reduce DB queries
_ban_cache = {}
_cache_ttl = 60

def check_ban(func):
    """Decorator to check if user is banned before executing any handler"""
    @wraps(func)
    async def wrapper(self, update, context):
        user_id = None
        
        # Get user ID from update
        if update.message and update.message.from_user:
            user_id = update.message.from_user.id
        elif update.callback_query and update.callback_query.from_user:
            user_id = update.callback_query.from_user.id
        elif update.effective_user:
            user_id = update.effective_user.id
        
        if user_id:
            # Check cache first
            now = time.time()
            if user_id in _ban_cache:
                cached_time, is_banned = _ban_cache[user_id]
                if now - cached_time < _cache_ttl:
                    if is_banned:
                        if update.callback_query:
                            await update.callback_query.answer("⛔ You are banned", show_alert=True)
                        elif update.message:
                            await update.message.reply_text("⛔ You have been banned from using this bot.")
                        return None
                    return await func(self, update, context)
            
            # Cache miss - query database
            db = SessionLocal()
            try:
                result = db.execute(
                    text("SELECT is_banned FROM users WHERE telegram_id = :uid"),
                    {"uid": user_id}
                ).fetchone()
                
                is_banned = result[0] if result else False
                _ban_cache[user_id] = (now, is_banned)
                
                if is_banned:
                    if update.callback_query:
                        await update.callback_query.answer("⛔ You are banned", show_alert=True)
                    elif update.message:
                        await update.message.reply_text("⛔ You have been banned from using this bot.")
                    return None
            except Exception as e:
                print(f"Ban check error: {e}")
            finally:
                db.close()
        
        return await func(self, update, context)
    
    return wrapper
