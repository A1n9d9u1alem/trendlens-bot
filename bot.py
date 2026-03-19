import os
import json
import redis
import requests
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy.orm import Session
from database import User, Content, UserInteraction, Payment, Analytics, ContentModeration, get_db, create_tables, SessionLocal
from payment_handler import PaymentHandler
from dotenv import load_dotenv
from ban_decorator import check_ban

load_dotenv()

class TrendLensBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_id = int(os.getenv('ADMIN_USER_ID', '0'))
        self.payment_handler = PaymentHandler()
        try:
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                if redis_url.startswith('redis://') and 'upstash.io' in redis_url:
                    redis_url = redis_url.replace('redis://', 'rediss://', 1)
                self.redis = redis.from_url(
                    redis_url,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                self.redis.ping()
                print("Redis connected - caching enabled")
            else:
                self.redis = None
                print("Redis not configured - caching disabled")
        except Exception as e:
            print(f"Redis connection failed: {e} - caching disabled")
            self.redis = None
        self.categories = ['memes', 'sports', 'entertainment', 'gaming', 'tech', 'news', 'jobs']
        self.tech_subcategories = {
            'ai_data': 'Artificial Intelligence & Data',
            'software': 'Software, Web & App Development', 
            'cyber': 'Cyber, Cloud & Networking',
            'hardware': 'Hardware, Robotics & Automation',
            'emerging': 'Emerging & Industry Technologies'
        }
        self.tech_keywords = {
            'ai_data': ['ai', 'artificial intelligence', 'machine learning', 'data science', 'neural network', 'deep learning', 'chatgpt', 'openai'],
            'software': ['programming', 'coding', 'web development', 'app development', 'javascript', 'python', 'react', 'nodejs'],
            'cyber': ['cybersecurity', 'cloud', 'aws', 'azure', 'networking', 'security', 'hacking', 'firewall'],
            'hardware': ['hardware', 'robotics', 'automation', 'iot', 'raspberry pi', 'arduino', 'electronics'],
            'emerging': ['blockchain', 'cryptocurrency', 'vr', 'ar', 'metaverse', '5g', 'quantum', 'nanotech']
        }
        self.category_keywords = {
            'memes': ['meme', 'funny', 'humor', 'joke', 'lol', 'dank', 'comedy', 'hilarious'],
            'sports': ['football', 'basketball', 'soccer', 'nba', 'nfl', 'sport', 'game', 'match', 'player', 'team', 'cricket', 'tennis', 'premier league', 'la liga', 'bundesliga', 'serie a', 'champions league', 'uefa', 'fifa', 'world cup', 'messi', 'ronaldo', 'goal', 'transfer', 'epl', 'ucl', 'boxing', 'fight', 'mma', 'ufc', 'knockout', 'fighter'],
            'entertainment': ['dance', 'music', 'celebrity', 'movie', 'tv', 'show', 'entertainment', 'actor', 'singer', 'artist'],
            'gaming': ['game', 'gaming', 'esports', 'nintendo', 'xbox', 'playstation', 'pc gaming', 'steam', 'twitch'],
            'tech': ['technology', 'software', 'ai', 'programming', 'computer', 'tech', 'digital', 'app', 'gadget'],
            'news': ['news', 'breaking', 'politics', 'world', 'update', 'report', 'current events'],
            'jobs': ['freelance', 'remote', 'hiring', 'upwork', 'fiverr', 'contract', 'gig', 'work from home', 'freelancer']
        }
        self.admin_rate_limit = {}  # Track admin command usage
        self.blocked_keywords = ['porn', 'xxx', 'sex', 'nude', 'nsfw', 'gore', 'violence']
    
    def calculate_trending_score(self, content):
        """Advanced trending algorithm considering recency, engagement velocity, and quality"""
        from datetime import datetime, timezone
        
        try:
            if isinstance(content, dict):
                created_at = content.get('created_at')
                engagement = float(content.get('engagement_score', 0) or 0)
                trend = float(content.get('trend_score', 0) or 0)
                views = int(content.get('views', 0) or 0)
                likes = int(content.get('likes', 0) or 0)
                comments = int(content.get('comments', 0) or 0)
            else:
                created_at = getattr(content, 'created_at', None)
                engagement = float(getattr(content, 'engagement_score', 0) or 0)
                trend = float(getattr(content, 'trend_score', 0) or 0)
                views = int(getattr(content, 'views', 0) or 0)
                likes = int(getattr(content, 'likes', 0) or 0)
                comments = int(getattr(content, 'comments', 0) or 0)
            
            # Time decay factor (newer = higher score)
            age_hours = 12  # Default
            if created_at:
                try:
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
                except:
                    age_hours = 12
            
            # Exponential decay: content loses 50% value every 12 hours
            time_factor = pow(0.5, age_hours / 12)
            
            # Engagement velocity (engagement per hour)
            if age_hours > 0:
                velocity = (likes + comments * 2) / age_hours
            else:
                velocity = likes + comments * 2
            
            # Viral coefficient (comments indicate discussion/virality)
            if likes > 0:
                viral_coefficient = min(comments / likes, 1.0) * 100
            else:
                viral_coefficient = 0
            
            # Calculate final trending score
            trending_score = (
                trend * 0.3 +                    # Base trend score (30%)
                engagement * 0.2 +               # Engagement score (20%)
                velocity * 0.25 +                # Engagement velocity (25%)
                viral_coefficient * 0.15 +       # Viral coefficient (15%)
                time_factor * 100 * 0.1          # Recency bonus (10%)
            )
            
            return trending_score
        except Exception as e:
            # Fallback to basic trend score if calculation fails
            if isinstance(content, dict):
                return float(content.get('trend_score', 0) or 0)
            else:
                return float(getattr(content, 'trend_score', 0) or 0)
    
    def sort_by_trending(self, contents):
        """Sort content by advanced trending algorithm"""
        try:
            scored_contents = []
            for content in contents:
                try:
                    trending_score = self.calculate_trending_score(content)
                    if isinstance(content, dict):
                        content['trending_score'] = trending_score
                    scored_contents.append((trending_score, content))
                except Exception as e:
                    # If scoring fails, use trend_score as fallback
                    if isinstance(content, dict):
                        fallback_score = float(content.get('trend_score', 0) or 0)
                    else:
                        fallback_score = float(getattr(content, 'trend_score', 0) or 0)
                    scored_contents.append((fallback_score, content))
            
            # Sort by trending score descending
            scored_contents.sort(key=lambda x: x[0], reverse=True)
            return [content for _, content in scored_contents]
        except Exception as e:
            # If entire sorting fails, return original list
            return contents
    
    def calculate_quality_score(self, content):
        """Calculate content quality score based on multiple factors"""
        score = 0
        
        if isinstance(content, dict):
            title = content.get('title', '')
            description = content.get('description', '')
            engagement = float(content.get('engagement_score', 0))
            trend = float(content.get('trend_score', 0))
            platform = content.get('platform', '')
        else:
            title = content.title
            description = content.description or ''
            engagement = float(content.engagement_score or 0)
            trend = float(content.trend_score or 0)
            platform = content.platform
        
        # Trend score weight (40%)
        score += trend * 0.4
        
        # Engagement score weight (30%)
        score += engagement * 0.3
        
        # Title quality (15%)
        title_len = len(title)
        if 20 <= title_len <= 100:  # Optimal length
            score += 15
        elif title_len > 10:
            score += 10
        
        # Has description (10%)
        if description and len(description) > 50:
            score += 10
        
        # Platform reliability (5%)
        platform_scores = {'reddit': 5, 'youtube': 4, 'twitter': 4, 'news': 5}
        score += platform_scores.get(platform.lower(), 2)
        
        return score
    
    def filter_quality_content(self, contents, min_quality=30):
        """Filter and sort content by quality score"""
        scored_contents = []
        for content in contents:
            quality_score = self.calculate_quality_score(content)
            if quality_score >= min_quality:
                if isinstance(content, dict):
                    content['quality_score'] = quality_score
                scored_contents.append((quality_score, content))
        
        # Sort by quality score descending
        scored_contents.sort(key=lambda x: x[0], reverse=True)
        return [content for _, content in scored_contents]
    
    def deduplicate_content(self, contents, seen_urls=None):
        """Remove duplicate content using hash and title similarity"""
        import hashlib
        from difflib import SequenceMatcher
        
        if seen_urls is None:
            seen_urls = set()
        
        unique_contents = []
        seen_hashes = set()
        seen_titles = []
        
        for content in contents:
            url = content.get('url') if isinstance(content, dict) else content.url
            title = (content.get('title') if isinstance(content, dict) else content.title).lower().strip()
            
            # Skip if URL already seen
            if url in seen_urls:
                continue
            
            # Generate content hash
            normalized = ''.join(c for c in title if c.isalnum())
            content_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
            
            # Skip if hash already seen
            if content_hash in seen_hashes:
                continue
            
            # Check title similarity (80% threshold)
            is_duplicate = False
            for seen_title in seen_titles:
                similarity = SequenceMatcher(None, title, seen_title).ratio()
                if similarity > 0.8:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            seen_urls.add(url)
            seen_hashes.add(content_hash)
            seen_titles.append(title)
            unique_contents.append(content)
        
        return unique_contents
    
    def track_analytics(self, db, user_id, event_type, category=None, metadata=None):
        """Track user analytics"""
        try:
            analytics = Analytics(
                user_id=user_id,
                event_type=event_type,
                category=category,
                event_data=json.dumps(metadata) if metadata else None
            )
            db.add(analytics)
            db.commit()
        except:
            pass
    
    def is_content_fresh(self, content_date, max_age_hours=48):
        """Check if content is fresh"""
        if not content_date:
            return False
        age = (datetime.now(timezone.utc) - content_date).total_seconds() / 3600
        return age <= max_age_hours
    
    def get_tech_subcategory(self, title, description=""):
        """Determine tech subcategory based on content"""
        text = f"{title} {description}".lower()
        
        for subcat, keywords in self.tech_keywords.items():
            if any(keyword in text for keyword in keywords):
                return subcat
        return 'software'  # Default fallback
    
    def validate_category_content(self, content, expected_category):
        if isinstance(content, dict):
            content_category = content.get('category', '')
            title = content.get('title', '').lower()
            description = content.get('description', '').lower()
        else:
            content_category = getattr(content, 'category', '')
            title = getattr(content, 'title', '').lower()
            description = getattr(content, 'description', '').lower() if getattr(content, 'description', None) else ''
        
        # First check if stored category matches
        if content_category != expected_category:
            return False
        
        # Additional validation using keywords to prevent cross-contamination
        text = f"{title} {description}"
        expected_keywords = self.category_keywords.get(expected_category, [])
        
        # Check if content contains keywords from the expected category
        has_expected_keywords = any(keyword in text for keyword in expected_keywords)
        
        # Check if content contains keywords from other categories (contamination check)
        for cat, keywords in self.category_keywords.items():
            if cat != expected_category:
                if any(keyword in text for keyword in keywords):
                    # Content contains keywords from another category - reject
                    return False
        
        return True
    
    def filter_content(self, title, description=""):
        """Filter inappropriate content"""
        text = f"{title} {description}".lower()
        for keyword in self.blocked_keywords:
            if keyword in text:
                return False
        return True
    
    def sanitize_input(self, text, max_length=200):
        """Sanitize user input"""
        if not text:
            return ""
        # Remove control characters and limit length
        import re
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(text))
        return text[:max_length].strip()
    
    def validate_payment_reference(self, reference):
        """Validate payment reference format"""
        import re
        # Allow alphanumeric, dash, underscore only
        if not re.match(r'^[a-zA-Z0-9_-]{5,100}$', reference):
            return False
        return True
    
    def check_admin_rate_limit(self, user_id, command, max_per_minute=10):
        """Rate limit admin commands"""
        now = datetime.now(timezone.utc)
        key = f"{user_id}_{command}"
        
        if key not in self.admin_rate_limit:
            self.admin_rate_limit[key] = []
        
        # Remove old entries (older than 1 minute)
        self.admin_rate_limit[key] = [
            t for t in self.admin_rate_limit[key] 
            if (now - t).total_seconds() < 60
        ]
        
        if len(self.admin_rate_limit[key]) >= max_per_minute:
            return False
        
        self.admin_rate_limit[key].append(now)
        return True
        
    def check_rate_limit(self, db_user):
        """Check if user exceeded rate limit"""
        if db_user.is_premium:
            return True
        
        # Check if columns exist
        if not hasattr(db_user, 'last_request') or not hasattr(db_user, 'request_count'):
            return True  # Skip rate limiting if columns don't exist
        
        now = datetime.now(timezone.utc)
        if db_user.last_request:
            # Ensure both datetimes are timezone-aware
            last_request = db_user.last_request
            if last_request.tzinfo is None:
                last_request = last_request.replace(tzinfo=timezone.utc)
            
            time_diff = (now - last_request).total_seconds()
            if time_diff > 86400:  # Reset daily
                db_user.request_count = 0
        
        if db_user.request_count >= 20:  # Free tier limit
            return False
        
        db_user.request_count += 1
        db_user.last_request = now
        return True
    
    @check_ban
    async def start_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle start callback from inline buttons"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
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
            
            if hasattr(db_user, 'is_banned') and db_user.is_banned:
                await query.edit_message_text("⛔ You have been banned from using this bot.")
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
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        finally:
            db.close()
    
    @check_ban
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            # Check if banned
            if hasattr(db_user, 'is_banned') and db_user.is_banned:
                await query.edit_message_text("⛔ You have been banned from using this bot.")
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
            
            await query.edit_message_text(
                "📂 Select a category to view trending content:\n\n"
                "🎯 Each category contains only relevant content - no mixing!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        finally:
            db.close()
    
    @check_ban
    async def show_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        try:
            parts = query.data.split('_')
            category = parts[1]
            time_filter = parts[2] if len(parts) > 2 else '48h'  # Default 48 hours
        except IndexError:
            await query.answer("❌ Invalid category. Try again.", show_alert=True)
            return
        
        if category not in self.categories:
            await query.answer("❌ Invalid category. Use /start to see available categories.", show_alert=True)
            return
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await query.answer("❌ User not found. Use /start first.", show_alert=True)
                return
            
            if hasattr(db_user, 'is_banned') and db_user.is_banned:
                await query.answer("⛔ You are banned from using this bot.", show_alert=True)
                return
            
            if not self.check_rate_limit(db_user):
                db.commit()
                await query.answer(
                    "⚠️ Daily limit reached!\n\nFree: 10/day | Pro: Unlimited\n\nUpgrade: /subscribe",
                    show_alert=True
                )
                return
            
            db.commit()
            limit = 20 if db_user.is_premium else 5
            
            # Calculate time cutoff based on filter
            if time_filter == 'today':
                cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_filter == 'week':
                cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            elif time_filter == '24h':
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            else:  # Default 48h
                cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
            
            # Trigger on-demand fetch for hot categories
            if category in ['sports', 'news']:
                try:
                    requests.get(f'http://localhost:3000/fetch/{category}', timeout=2)
                except:
                    pass
            
            # Get from cache first with shorter timeout
            cached = []
            cache_key = f"trending:{category}:{time_filter}"
            if self.redis:
                try:
                    # Set shorter timeout for cache operations
                    cached = self.redis.zrevrange(cache_key, 0, limit-1)
                    if cached and len(cached) >= limit:
                        print(f"Cache hit for {category}:{time_filter}: {len(cached)} items")
                        # Use cached data immediately
                        contents = []
                        for item_bytes in cached[:limit]:
                            try:
                                item = json.loads(item_bytes.decode('utf-8'))
                                if item.get('category') == category:
                                    contents.append(item)
                            except:
                                continue
                        
                        if len(contents) >= limit:
                            # Send immediately from cache
                            context.user_data['category'] = category
                            context.user_data['contents'] = contents[:limit]
                            context.user_data['index'] = 0
                            context.user_data['time_filter'] = time_filter
                            
                            await self.send_content_with_filters(query, contents[0], 0, len(contents[:limit]), db_user.is_premium, category, time_filter)
                            return
                except Exception as e:
                    print(f"Cache error: {e}")
                    cached = []
            
            if cached:
                # Use cached content and filter by time
                contents = []
                for item_bytes in cached:
                    try:
                        item = json.loads(item_bytes.decode('utf-8'))
                        # Validate category matches
                        if item.get('category') == category:
                            # Skip cached content for time filters - force database query
                            if time_filter != '48h':
                                continue
                            contents.append(item)
                    except:
                        continue
                
                # If time filter is not default, skip cache and use database
                if time_filter != '48h':
                    contents = []
                
                if contents:
                    contents = self.deduplicate_content(contents)
                    contents = self.filter_quality_content(contents, min_quality=30)
                    contents = self.sort_by_trending(contents)
                    
                    if len(contents) >= limit:
                        contents = contents[:limit]
            
            if not cached or not contents:
                # Optimized query - use only indexed columns
                if category == 'memes':
                    db_contents = db.query(Content).filter(
                        Content.category == 'memes',
                        Content.created_at >= cutoff
                    ).order_by(Content.trend_score.desc()).limit(limit).all()
                elif category == 'sports':
                    db_contents = db.query(Content).filter(
                        Content.category == 'sports',
                        Content.created_at >= cutoff
                    ).order_by(Content.trend_score.desc()).limit(limit).all()
                elif category == 'entertainment':
                    db_contents = db.query(Content).filter(
                        Content.category == 'entertainment',
                        Content.created_at >= cutoff
                    ).order_by(Content.trend_score.desc()).limit(limit).all()
                elif category == 'gaming':
                    db_contents = db.query(Content).filter(
                        Content.category == 'gaming',
                        Content.created_at >= cutoff
                    ).order_by(Content.trend_score.desc()).limit(limit).all()
                elif category == 'jobs':
                    db_contents = db.query(Content).filter(
                        Content.category == 'jobs',
                        Content.created_at >= cutoff
                    ).order_by(Content.trend_score.desc()).limit(limit).all()
                elif category == 'news':
                    db_contents = db.query(Content).filter(
                        Content.category == 'news',
                        Content.created_at >= cutoff
                    ).order_by(Content.trend_score.desc()).limit(limit).all()
                elif category == 'tech':
                    db_contents = db.query(Content).filter(
                        Content.category == 'tech',
                        Content.created_at >= cutoff
                    ).order_by(Content.trend_score.desc()).limit(limit).all()
                else:
                    db_contents = []
                
                # Convert to dict format and cache
                contents = []
                for c in db_contents:
                    content_dict = {
                        'id': c.id,
                        'title': c.title,
                        'url': c.url,
                        'platform': c.platform,
                        'category': c.category,
                        'thumbnail': c.thumbnail,
                        'description': c.description,
                        'engagement_score': c.engagement_score,
                        'trend_score': c.trend_score
                    }
                    contents.append(content_dict)
                
                contents = self.deduplicate_content(contents)
                contents = self.filter_quality_content(contents, min_quality=30)
                contents = self.sort_by_trending(contents)
                
                # Cache to Redis with time filter key
                if self.redis and contents:
                    try:
                        for content_dict in contents[:limit]:
                            self.redis.zadd(
                                cache_key,
                                {json.dumps(content_dict): content_dict.get('trend_score', 0)}
                            )
                        self.redis.expire(cache_key, 120)  # 2 min cache for real-time
                    except:
                        pass
            

            # Track analytics
            self.track_analytics(db, db_user.id, 'category_view', category)
            
            if not contents:
                await query.edit_message_text(
                    f"No trending content found for {category}.\n\nTry again later!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="categories")]])
                )
                return
            
            # Show first item with time filter buttons
            context.user_data['category'] = category
            context.user_data['contents'] = contents
            context.user_data['index'] = 0
            context.user_data['time_filter'] = time_filter
            
            await self.send_content_with_filters(query, contents[0], 0, len(contents), db_user.is_premium, category, time_filter)
        finally:
            db.close()
    
    async def send_content_with_filters(self, query, content, index, total, is_premium, category, time_filter='48h'):
        if isinstance(content, dict):
            title = content['title']
            url = content['url']
            platform = content['platform']
            description = content.get('description', '')
        else:
            title = content.title
            url = content.url
            platform = content.platform
            description = content.description or ''
        
        # Time filter label
        filter_labels = {'today': '🔥 Today', 'week': '📅 This Week', '24h': '⏰ 24 Hours', '48h': '🕒 48 Hours'}
        filter_label = filter_labels.get(time_filter, '🕒 48 Hours')
        
        text = f"{filter_label}\n\n🔥 {title}\n\n📱 Platform: {platform.upper()}\n"
        if is_premium and description:
            text += f"📝 {description[:150]}...\n\n"
        text += f"🔗 {url}\n\n📊 Item {index+1}/{total}"
        
        keyboard = []
        
        # Time filter buttons (Pro only)
        if is_premium:
            filter_row = []
            if time_filter != 'today':
                filter_row.append(InlineKeyboardButton("🔥 Today", callback_data=f"cat_{category}_today"))
            if time_filter != '24h':
                filter_row.append(InlineKeyboardButton("⏰ 24h", callback_data=f"cat_{category}_24h"))
            if time_filter != 'week':
                filter_row.append(InlineKeyboardButton("📅 Week", callback_data=f"cat_{category}_week"))
            if filter_row:
                keyboard.append(filter_row)
        
        # Navigation
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
    
    @check_ban
    async def navigate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    async def subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            # Check if banned
            if hasattr(db_user, 'is_banned') and db_user.is_banned:
                await query.edit_message_text("⛔ You have been banned from using this bot.")
                return
            
            if db_user.is_premium and db_user.subscription_end:
                # Ensure subscription_end is timezone-aware
                sub_end = db_user.subscription_end
                if sub_end.tzinfo is None:
                    sub_end = sub_end.replace(tzinfo=timezone.utc)
                
                if sub_end > datetime.now(timezone.utc):
                    days_left = (sub_end - datetime.now(timezone.utc)).days
                    await query.edit_message_text(
                        f"✅ You're already a Pro member!\n\n"
                        f"⏰ {days_left} days remaining\n\n"
                        f"Expires: {sub_end.strftime('%Y-%m-%d')}",
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
        finally:
            db.close()
    
    async def show_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            self.payment_handler.create_payment_request(db_user.id, 5.0, db)
            
            await query.edit_message_text(
                self.payment_handler.get_payment_message(),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="subscribe")]])
            )
        finally:
            db.close()
    
    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide payment reference\n\n"
                "Usage: /confirm <reference>\n"
                "Example: /confirm TX123456789"
            )
            return
        
        reference = self.sanitize_input(' '.join(context.args), max_length=100)
        
        if not self.validate_payment_reference(reference):
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
        finally:
            db.close()
    
    async def account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if db_user.is_premium and db_user.subscription_end:
                # Ensure subscription_end is timezone-aware
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
    
    async def approve_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not self.check_admin_rate_limit(update.effective_user.id, 'approve', max_per_minute=5):
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
        finally:
            db.close()
    
    async def reject_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not self.check_admin_rate_limit(update.effective_user.id, 'reject', max_per_minute=5):
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
        finally:
            db.close()
    
    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        db = SessionLocal()
        try:
            total_users = db.query(User).count()
            pro_users = db.query(User).filter(User.is_premium == True).count()
            free_users = total_users - pro_users
            pending_payments = db.query(Payment).filter(Payment.status == 'submitted').count()
            approved_payments = db.query(Payment).filter(Payment.status == 'approved').count()
            rejected_payments = db.query(Payment).filter(Payment.status == 'rejected').count()
            
            # Active users (last 7 days)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            active_users = db.query(User).filter(User.created_at >= week_ago).count()
            
            # New users today
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
    
    async def revoke_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not self.check_admin_rate_limit(update.effective_user.id, 'revoke', max_per_minute=5):
            await update.message.reply_text("⚠️ Rate limit exceeded. Wait a minute.")
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
        
        db = SessionLocal()
        try:
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
        finally:
            db.close()
    
    async def list_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        db = SessionLocal()
        try:
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
        finally:
            db.close()
    
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not self.check_admin_rate_limit(update.effective_user.id, 'broadcast', max_per_minute=2):
            await update.message.reply_text("⚠️ Rate limit exceeded. Wait a minute.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: /broadcast <message>\n"
                "Example: /broadcast New features coming soon!"
            )
            return
        
        message = self.sanitize_input(' '.join(context.args), max_length=4000)
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
                    await asyncio.sleep(0.05)  # Rate limit
                except Exception as e:
                    failed += 1
            
            await update.message.reply_text(
                f"✅ Broadcast complete\n\n"
                f"✅ Sent: {sent}\n"
                f"❌ Failed: {failed}"
            )
        finally:
            db.close()
    
    async def grant_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not self.check_admin_rate_limit(update.effective_user.id, 'grant', max_per_minute=5):
            await update.message.reply_text("⚠️ Rate limit exceeded. Wait a minute.")
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
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            
            if not user:
                await update.message.reply_text("❌ User not found")
                return
            
            user.is_premium = True
            # Ensure subscription_end is timezone-aware before comparison
            sub_end = user.subscription_end
            if sub_end and sub_end.tzinfo is None:
                sub_end = sub_end.replace(tzinfo=timezone.utc)
            
            if sub_end and sub_end > datetime.now(timezone.utc):
                user.subscription_end = sub_end + timedelta(days=days)
            else:
                user.subscription_end = datetime.now(timezone.utc) + timedelta(days=days)
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
        finally:
            db.close()
    
    async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not self.check_admin_rate_limit(update.effective_user.id, 'ban', max_per_minute=5):
            await update.message.reply_text("⚠️ Rate limit exceeded. Wait a minute.")
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
        
        db = SessionLocal()
        try:
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
        finally:
            db.close()
    
    async def analytics_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        db = SessionLocal()
        try:
            from collections import Counter
            days = int(context.args[0]) if context.args else 7
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            total_users = db.query(User).count()
            new_users = db.query(User).filter(User.created_at >= cutoff).count()
            pro_users = db.query(User).filter(User.is_premium == True).count()
            active_users = db.query(Analytics).filter(Analytics.timestamp >= cutoff).distinct(Analytics.user_id).count()
            
            events = db.query(Analytics).filter(Analytics.timestamp >= cutoff).all()
            event_counts = Counter([e.event_type for e in events])
            category_views = Counter([e.category for e in events if e.category])
            
            total_content = db.query(Content).count()
            new_content = db.query(Content).filter(Content.created_at >= cutoff).count()
            
            pending_payments = db.query(Payment).filter(Payment.status == 'submitted').count()
            approved_payments = db.query(Payment).filter(Payment.status == 'approved', Payment.approved_at >= cutoff).count()
            revenue = approved_payments * 5
            
            retention = (active_users / total_users * 100) if total_users > 0 else 0
            conversion = (pro_users / total_users * 100) if total_users > 0 else 0
            
            text = f"📊 Advanced Analytics ({days}d)\n\n"
            text += f"👥 Users:\n"
            text += f"  Total: {total_users}\n"
            text += f"  New: {new_users}\n"
            text += f"  Active: {active_users} ({retention:.1f}%)\n"
            text += f"  Pro: {pro_users} ({conversion:.1f}%)\n\n"
            
            text += f"📄 Content:\n"
            text += f"  Total: {total_content}\n"
            text += f"  New: {new_content}\n\n"
            
            text += f"💰 Revenue:\n"
            text += f"  Approved: {approved_payments}\n"
            text += f"  Pending: {pending_payments}\n"
            text += f"  Total: ${revenue}\n\n"
            
            text += f"📊 Events:\n"
            for event, count in event_counts.most_common(5):
                text += f"  {event}: {count}\n"
            
            text += f"\n📂 Top Categories:\n"
            for cat, count in category_views.most_common(5):
                text += f"  {cat}: {count}\n"
            
            await update.message.reply_text(text)
        finally:
            db.close()
    
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
        
        db = SessionLocal()
        try:
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
        finally:
            db.close()
    
    @check_ban
    async def saved(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            
            await update.message.reply_text(f"💾 Your Saved Content ({len(contents)} items)")
            await self.send_saved_content(update.message, contents[0], 0, len(contents))
        except Exception as e:
            import logging
            logging.error(f"Saved content error: {e}")
            await update.message.reply_text(
                "❌ Failed to load saved content.\n\n"
                "Please try again or contact support."
            )
        finally:
            db.close()
    
    async def send_saved_content(self, message, content, index, total):
        text = f"💾 Saved Content\n\n🔥 {content['title']}\n\n📁 {content['category'].title()}\n📱 {content['platform'].upper()}\n"
        if content.get('description'):
            text += f"📝 {content['description'][:150]}...\n\n"
        text += f"🔗 {content['url']}\n\n📊 {index+1}/{total}"
        
        keyboard = []
        nav_row = []
        if index > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data="saved_prev"))
        if index < total - 1:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data="saved_next"))
        if nav_row:
            keyboard.append(nav_row)
        
        keyboard.append([InlineKeyboardButton("🔗 Open", url=content['url'])])
        keyboard.append([InlineKeyboardButton("« Back", callback_data="start")])
        
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    @check_ban
    async def saved_navigate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        direction = query.data.split('_')[1]
        contents = context.user_data.get('contents', [])
        index = context.user_data.get('index', 0)
        
        if not contents:
            await query.answer("No saved content", show_alert=True)
            return
        
        if direction == 'next' and index < len(contents) - 1:
            index += 1
        elif direction == 'prev' and index > 0:
            index -= 1
        
        context.user_data['index'] = index
        content = contents[index]
        
        text = f"💾 Saved Content\n\n🔥 {content['title']}\n\n📁 {content['category'].title()}\n📱 {content['platform'].upper()}\n"
        if content.get('description'):
            text += f"📝 {content['description'][:150]}...\n\n"
        text += f"🔗 {content['url']}\n\n📊 {index+1}/{len(contents)}"
        
        keyboard = []
        nav_row = []
        if index > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data="saved_prev"))
        if index < len(contents) - 1:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data="saved_next"))
        if nav_row:
            keyboard.append(nav_row)
        
        keyboard.append([InlineKeyboardButton("🔗 Open", url=content['url'])])
        keyboard.append([InlineKeyboardButton("« Back", callback_data="start")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    @check_ban
    async def search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "🔍 Search Usage:\n\n"
                "/search <keywords>\n\n"
                "Example: /search messi goal\n"
                "Example: /search ai chatgpt"
            )
            return
        
        query = ' '.join(context.args).lower()
        user = update.effective_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await update.message.reply_text("❌ User not found. Use /start first.")
                return
            
            if not self.check_rate_limit(db_user):
                db.commit()
                await update.message.reply_text(
                    "⚠️ Daily limit reached!\n\n"
                    "🎆 Free users: 10 requests/day\n"
                    "⭐ Pro users: Unlimited\n\n"
                    "Upgrade: /subscribe"
                )
                return
            
            db.commit()
            limit = 20 if db_user.is_premium else 5
            
            from sqlalchemy import or_
            cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
            results = db.query(Content).filter(
                Content.created_at >= cutoff,
                or_(
                    Content.title.ilike(f'%{query}%'),
                    Content.description.ilike(f'%{query}%')
                )
            ).order_by(Content.trend_score.desc()).limit(limit).all()
            
            if not results:
                await update.message.reply_text(
                    f"🔍 No results for '{query}'\n\n"
                    "💡 Tips:\n"
                    "• Try different keywords\n"
                    "• Use simpler terms\n"
                    "• Check spelling\n\n"
                    "Browse categories: /start"
                )
                return
            
            contents = [{
                'id': c.id, 'title': c.title, 'url': c.url, 'platform': c.platform,
                'category': c.category, 'thumbnail': c.thumbnail, 'description': c.description
            } for c in results]
            
            # Deduplicate search results
            contents = self.deduplicate_content(contents)
            
            # Apply quality filtering to search results
            contents = self.filter_quality_content(contents, min_quality=25)
            
            # Apply trending algorithm to search results
            contents = self.sort_by_trending(contents)
            
            self.track_analytics(db, db_user.id, 'search', metadata={'query': query, 'results': len(contents)})
            
            context.user_data['contents'] = contents
            context.user_data['index'] = 0
            context.user_data['search_query'] = query
            
            await update.message.reply_text(f"🔍 Found {len(contents)} results for '{query}'")
            await self.send_search_result(update.message, contents[0], 0, len(contents), db_user.is_premium, query)
        except Exception as e:
            import logging
            logging.error(f"Search error: {e}")
            await update.message.reply_text(
                "❌ Search failed.\n\n"
                "Please try again or contact support if this persists."
            )
        finally:
            db.close()
    
    async def send_search_result(self, message, content, index, total, is_premium, query):
        title = content['title']
        url = content['url']
        platform = content['platform']
        category = content['category']
        description = content.get('description', '')
        
        text = f"🔍 '{query}'\n\n🔥 {title}\n\n📁 {category.title()}\n📱 {platform.upper()}\n"
        if is_premium and description:
            text += f"📝 {description[:150]}...\n\n"
        text += f"🔗 {url}\n\n📊 {index+1}/{total}"
        
        keyboard = []
        nav_row = []
        if index > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data="search_prev"))
        if index < total - 1:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data="search_next"))
        if nav_row:
            keyboard.append(nav_row)
        
        keyboard.append([InlineKeyboardButton("🔗 Open", url=url)])
        keyboard.append([InlineKeyboardButton("« Categories", callback_data="categories")])
        
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    @check_ban
    async def search_navigate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        direction = query.data.split('_')[1]
        contents = context.user_data.get('contents', [])
        index = context.user_data.get('index', 0)
        search_query = context.user_data.get('search_query', '')
        
        if not contents:
            await query.answer("No results", show_alert=True)
            return
        
        if direction == 'next' and index < len(contents) - 1:
            index += 1
        elif direction == 'prev' and index > 0:
            index -= 1
        
        context.user_data['index'] = index
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            content = contents[index]
            
            text = f"🔍 '{search_query}'\n\n🔥 {content['title']}\n\n📁 {content['category'].title()}\n📱 {content['platform'].upper()}\n"
            if db_user.is_premium and content.get('description'):
                text += f"📝 {content['description'][:150]}...\n\n"
            text += f"🔗 {content['url']}\n\n📊 {index+1}/{len(contents)}"
            
            keyboard = []
            nav_row = []
            if index > 0:
                nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data="search_prev"))
            if index < len(contents) - 1:
                nav_row.append(InlineKeyboardButton("Next ➡️", callback_data="search_next"))
            if nav_row:
                keyboard.append(nav_row)
            
            keyboard.append([InlineKeyboardButton("🔗 Open", url=content['url'])])
            keyboard.append([InlineKeyboardButton("« Categories", callback_data="categories")])
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await query.answer("Error", show_alert=True)
        finally:
            db.close()
    
    async def trending(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        category = context.args[0] if context.args else 'memes'
        
        if category not in self.categories:
            await update.message.reply_text(f"Invalid category. Choose from: {', '.join(self.categories)}")
            return
        
        user = update.effective_user
        db = SessionLocal()
        try:
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
        finally:
            db.close()
    
    async def save_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                        # Check if already saved
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
                            self.track_analytics(db, db_user.id, 'content_save', metadata={'content_id': content_id})
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
    
    async def show_tech_subcategories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🤖 AI & Data", callback_data="techcat_ai_data")],
            [InlineKeyboardButton("💻 Software & Web", callback_data="techcat_software")],
            [InlineKeyboardButton("🔒 Cyber & Cloud", callback_data="techcat_cyber")],
            [InlineKeyboardButton("🔧 Hardware & Robotics", callback_data="techcat_hardware")],
            [InlineKeyboardButton("🚀 Emerging Tech", callback_data="techcat_emerging")],
            [InlineKeyboardButton("« Back", callback_data="categories")]
        ]
        
        await query.edit_message_text(
            "💻 Tech Categories:\n\n🎯 Select a specific tech area:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_tech_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        try:
            # Parse callback data: techcat_ai_data -> ai_data
            parts = query.data.split('_')
            if len(parts) >= 3:
                subcategory = '_'.join(parts[1:])
            else:
                subcategory = parts[1] if len(parts) > 1 else ''
        except:
            await query.answer("❌ Invalid subcategory", show_alert=True)
            return
        
        if subcategory not in self.tech_subcategories:
            await query.answer("❌ Invalid subcategory", show_alert=True)
            return
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not self.check_rate_limit(db_user):
                db.commit()
                await query.answer("⚠️ Daily limit reached!", show_alert=True)
                return
            
            db.commit()
            limit = 20 if db_user.is_premium else 5
            
            # Get tech content and filter by subcategory
            cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
            from sqlalchemy import or_
            db_contents = db.query(Content).filter(
                Content.category == 'tech',
                Content.created_at >= cutoff,
                or_(Content.url.like('%/r/technology/%'), Content.url.like('%/r/programming/%'), Content.url.like('%/r/gadgets/%'))
            ).order_by(Content.trend_score.desc()).limit(50).all()
            
            # Filter by subcategory keywords
            filtered_contents = []
            keywords = self.tech_keywords.get(subcategory, [])
            
            for c in db_contents:
                text = f"{c.title} {c.description or ''}".lower()
                if any(keyword in text for keyword in keywords):
                    filtered_contents.append({
                        'id': c.id,
                        'title': c.title,
                        'url': c.url,
                        'platform': c.platform,
                        'category': c.category,
                        'subcategory': subcategory,
                        'thumbnail': c.thumbnail,
                        'description': c.description,
                        'engagement_score': c.engagement_score,
                        'trend_score': c.trend_score
                    })
                    if len(filtered_contents) >= limit * 2:  # Get more for deduplication
                        break
            
            # Deduplicate tech content
            filtered_contents = self.deduplicate_content(filtered_contents)
            
            # Apply quality filtering
            filtered_contents = self.filter_quality_content(filtered_contents, min_quality=30)
            filtered_contents = filtered_contents[:limit]
            
            if not filtered_contents:
                await query.edit_message_text(
                    f"No content found for {self.tech_subcategories[subcategory]}.\n\nTry again later!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="cat_tech")]])
                )
                return
            
            context.user_data['category'] = f'tech_{subcategory}'
            context.user_data['contents'] = filtered_contents
            context.user_data['index'] = 0
            
            await self.send_content(query, filtered_contents[0], 0, len(filtered_contents), db_user.is_premium)
        finally:
            db.close()
    
    @check_ban
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if hasattr(db_user, 'is_banned') and db_user.is_banned:
                await query.edit_message_text("⛔ You have been banned from using this bot.")
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
            
            await query.edit_message_text(
                f"⚙️ Settings\n\n"
                f"👤 Status: {status}\n\n"
                f"Manage your preferences:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        finally:
            db.close()
    
    async def account_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            status = '✨ Pro Member' if db_user.is_premium else '🆓 Free Member'
            
            if db_user.is_premium and db_user.subscription_end:
                sub_end = db_user.subscription_end
                if sub_end.tzinfo is None:
                    sub_end = sub_end.replace(tzinfo=timezone.utc)
                
                if sub_end > datetime.now(timezone.utc):
                    days_left = (sub_end - datetime.now(timezone.utc)).days
                    sub_info = f"⏰ {days_left} days remaining\n📅 Expires: {sub_end.strftime('%Y-%m-%d')}"
                else:
                    sub_info = "⚠️ Subscription expired"
            else:
                sub_info = "Upgrade to Pro for unlimited access!"
            
            joined_date = db_user.created_at.strftime('%Y-%m-%d') if db_user.created_at else 'Unknown'
            
            text = (
                f"👤 Account Information\n\n"
                f"🆔 User ID: {user.id}\n"
                f"👤 Username: @{user.username or user.first_name}\n"
                f"📅 Joined: {joined_date}\n\n"
                f"📊 Status: {status}\n"
                f"{sub_info}"
            )
            
            keyboard = [[InlineKeyboardButton("« Back", callback_data="settings")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        finally:
            db.close()
    
    async def my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            # Get user analytics
            total_views = db.query(Analytics).filter(
                Analytics.user_id == db_user.id,
                Analytics.event_type == 'category_view'
            ).count()
            
            saved_content = db.query(UserInteraction).filter(
                UserInteraction.user_id == db_user.id,
                UserInteraction.action == 'save'
            ).count()
            
            # Most viewed category
            from collections import Counter
            views = db.query(Analytics).filter(
                Analytics.user_id == db_user.id,
                Analytics.category.isnot(None)
            ).all()
            
            if views:
                category_counts = Counter([v.category for v in views])
                top_category = category_counts.most_common(1)[0][0] if category_counts else 'None'
            else:
                top_category = 'None'
            
            text = (
                f"📊 Your Statistics\n\n"
                f"👁️ Total Views: {total_views}\n"
                f"💾 Saved Content: {saved_content}\n"
                f"⭐ Favorite Category: {top_category.title()}\n\n"
                f"Keep exploring trending content!"
            )
            
            keyboard = [[InlineKeyboardButton("« Back", callback_data="settings")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        finally:
            db.close()
    
    async def notifications_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if db_user.is_premium:
                text = (
                    "🔔 Notification Settings\n\n"
                    "✅ Trending Alerts: ENABLED\n\n"
                    "📢 You'll receive notifications for:\n"
                    "• New viral content in your favorite categories\n"
                    "• Breaking news and trending topics\n"
                    "• Payment confirmations\n"
                    "• Subscription updates\n"
                    "• Important announcements\n\n"
                    "💡 Notifications sent hourly for trending content (score > 80)\n\n"
                    "⚙️ Manage via Telegram settings"
                )
            else:
                text = (
                    "🔔 Notification Settings\n\n"
                    "📢 You'll receive notifications for:\n"
                    "• Payment confirmations\n"
                    "• Subscription updates\n"
                    "• Important announcements\n\n"
                    "⭐ Upgrade to Pro for:\n"
                    "• Trending content alerts\n"
                    "• Breaking news notifications\n"
                    "• Personalized recommendations\n\n"
                    "👉 /subscribe to upgrade"
                )
        finally:
            db.close()
        
        keyboard = [[InlineKeyboardButton("« Back", callback_data="settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def view_saved_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user.is_premium:
                await query.edit_message_text(
                    "⭐ Saved Content is a Pro feature!\n\n"
                    "Upgrade to Pro to save and bookmark content.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="settings")]])
                )
                return
            
            interactions = db.query(UserInteraction).filter(
                UserInteraction.user_id == db_user.id,
                UserInteraction.action == 'save'
            ).order_by(UserInteraction.timestamp.desc()).limit(20).all()
            
            if not interactions:
                await query.edit_message_text(
                    "💾 No saved content yet!\n\n"
                    "Click 💾 Save button while browsing to bookmark content.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="settings")]])
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
                await query.edit_message_text(
                    "💾 No saved content available.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="settings")]])
                )
                return
            
            context.user_data['contents'] = contents
            context.user_data['index'] = 0
            
            content = contents[0]
            text = f"💾 Saved Content ({len(contents)} items)\n\n🔥 {content['title']}\n\n📁 {content['category'].title()}\n📱 {content['platform'].upper()}\n"
            if content.get('description'):
                text += f"📝 {content['description'][:150]}...\n\n"
            text += f"🔗 {content['url']}\n\n📊 1/{len(contents)}"
            
            keyboard = []
            if len(contents) > 1:
                keyboard.append([InlineKeyboardButton("Next ➡️", callback_data="saved_next")])
            keyboard.append([InlineKeyboardButton("🔗 Open", url=content['url'])])
            keyboard.append([InlineKeyboardButton("« Settings", callback_data="settings")])
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        finally:
            db.close()
    
    async def help_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        text = (
            "❓ Help & Support\n\n"
            "📚 Available Commands:\n"
            "• /start - Main menu\n"
            "• /search <keywords> - Search content\n"
            "• /saved - View saved content (Pro)\n"
            "• /trending <category> - View trends\n"
            "• /account - Account status\n"
            "• /confirm <ref> - Confirm payment\n\n"
            "🔍 Search Examples:\n"
            "• /search messi goal\n"
            "• /search ai chatgpt\n"
            "• /search funny meme\n\n"
            "📂 Quick Guide:\n"
            "• Browse categories for trending content\n"
            "• Use Next/Prev to navigate\n"
            "• Save content (Pro feature)\n"
            "• Upgrade to Pro for unlimited access\n\n"
            "💳 Payment:\n"
            "Use /confirm <reference> after payment\n\n"
            "📞 Support:\n"
            "Contact admin for assistance"
        )
        
        keyboard = [[InlineKeyboardButton("« Back", callback_data="settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def moderation_queue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        db = SessionLocal()
        try:
            pending = db.query(ContentModeration).filter(
                ContentModeration.status == 'pending'
            ).order_by(ContentModeration.moderated_at.desc()).limit(10).all()
            
            if not pending:
                await update.message.reply_text("✅ No pending content to moderate")
                return
            
            text = f"🔍 Content Moderation Queue ({len(pending)} pending)\n\n"
            for mod in pending:
                content = db.query(Content).filter(Content.id == mod.content_id).first()
                if content:
                    text += f"ID: {mod.id}\n📝 {content.title[:50]}...\n🔗 {content.url}\n\n"
            
            text += "Commands:\n/approve_content <id>\n/reject_content <id> <reason>"
            await update.message.reply_text(text)
        finally:
            db.close()
    
    async def approve_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /approve_content <moderation_id>")
            return
        
        db = SessionLocal()
        try:
            mod_id = int(context.args[0])
            mod = db.query(ContentModeration).filter(ContentModeration.id == mod_id).first()
            
            if not mod:
                await update.message.reply_text("❌ Moderation entry not found")
                return
            
            mod.status = 'approved'
            mod.moderated_by = self.admin_id
            mod.moderated_at = datetime.now(timezone.utc)
            db.commit()
            
            await update.message.reply_text(f"✅ Content {mod_id} approved")
        finally:
            db.close()
    
    async def reject_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /reject_content <moderation_id> <reason>")
            return
        
        db = SessionLocal()
        try:
            mod_id = int(context.args[0])
            reason = ' '.join(context.args[1:])
            
            mod = db.query(ContentModeration).filter(ContentModeration.id == mod_id).first()
            
            if not mod:
                await update.message.reply_text("❌ Moderation entry not found")
                return
            
            mod.status = 'rejected'
            mod.reason = reason
            mod.moderated_by = self.admin_id
            mod.moderated_at = datetime.now(timezone.utc)
            db.commit()
            
            await update.message.reply_text(f"❌ Content {mod_id} rejected: {reason}")
        finally:
            db.close()
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors with user-friendly messages"""
        import logging
        import traceback
        
        error = context.error
        logging.error(f"Update {update} caused error {error}")
        logging.error(traceback.format_exc())
        
        try:
            if update and update.effective_message:
                error_msg = "⚠️ Something went wrong.\n\n"
                
                # Specific error messages
                if "timeout" in str(error).lower():
                    error_msg += "⏱️ Request timed out. Please try again."
                elif "network" in str(error).lower() or "connection" in str(error).lower():
                    error_msg += "🌐 Network issue. Check your connection and retry."
                elif "database" in str(error).lower():
                    error_msg += "💾 Database temporarily unavailable. Try again in a moment."
                elif "rate" in str(error).lower() or "flood" in str(error).lower():
                    error_msg += "🐌 Too many requests. Please wait a moment."
                else:
                    error_msg += "🔧 Unexpected error occurred. Please try again.\n\nIf this persists, contact support."
                
                await update.effective_message.reply_text(error_msg)
        except Exception as e:
            logging.error(f"Error in error_handler: {e}")
    
    def run(self):
        import logging
        import sys
        
        # Fix Windows console encoding for Unicode
        if sys.platform == 'win32':
            import os
            os.system('chcp 65001 >nul 2>&1')
        
        logging.basicConfig(level=logging.INFO)
        
        # Set up event loop for Python 3.14+ compatibility
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        app = Application.builder().token(self.token).build()
        
        # Add error handler
        app.add_error_handler(self.error_handler)
        
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("saved", self.saved))
        app.add_handler(CommandHandler("search", self.search))
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
        app.add_handler(CommandHandler("analytics", self.analytics_report))
        app.add_handler(CommandHandler("moderate", self.moderation_queue))
        app.add_handler(CommandHandler("approve_content", self.approve_content))
        app.add_handler(CommandHandler("reject_content", self.reject_content))
        app.add_handler(CallbackQueryHandler(self.show_categories, pattern="^categories$"))
        app.add_handler(CallbackQueryHandler(self.show_tech_subcategories, pattern="^cat_tech$"))
        app.add_handler(CallbackQueryHandler(self.show_tech_category, pattern="^techcat_"))
        app.add_handler(CallbackQueryHandler(self.show_category, pattern="^cat_[a-z]+(_[a-z0-9]+)?$"))
        app.add_handler(CallbackQueryHandler(self.navigate, pattern="^nav_"))
        app.add_handler(CallbackQueryHandler(self.search_navigate, pattern="^search_"))
        app.add_handler(CallbackQueryHandler(self.saved_navigate, pattern="^saved_"))
        app.add_handler(CallbackQueryHandler(self.save_content, pattern="^save_"))
        app.add_handler(CallbackQueryHandler(self.subscribe, pattern="^subscribe$"))
        app.add_handler(CallbackQueryHandler(self.show_payment, pattern="^show_payment$"))
        app.add_handler(CallbackQueryHandler(self.start_callback, pattern="^start$"))
        app.add_handler(CallbackQueryHandler(self.settings, pattern="^settings$"))
        app.add_handler(CallbackQueryHandler(self.view_saved_callback, pattern="^view_saved$"))
        app.add_handler(CallbackQueryHandler(self.account_info, pattern="^account_info$"))
        app.add_handler(CallbackQueryHandler(self.my_stats, pattern="^my_stats$"))
        app.add_handler(CallbackQueryHandler(self.notifications_settings, pattern="^notifications_settings$"))
        app.add_handler(CallbackQueryHandler(self.help_support, pattern="^help_support$"))
        
        try:
            print("🤖 TrendLens AI Bot started!")
            print(f"👤 Admin ID: {self.admin_id}")
        except UnicodeEncodeError:
            print("TrendLens AI Bot started!")
            print(f"Admin ID: {self.admin_id}")
        app.run_polling()

if __name__ == '__main__':
    bot = TrendLensBot()
    bot.run()

    async def language_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")],
            [InlineKeyboardButton("🇪🇹 አማርኛ (Amharic)", callback_data="set_lang_am")],
            [InlineKeyboardButton("« Back", callback_data="settings")]
        ]
        
        await query.edit_message_text(
            "🌍 Select Language / ቋንቋ ይምረጡ:\n\n"
            "Choose your preferred language:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def set_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        lang = query.data.split('_')[2]
        user = query.from_user
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if db_user:
                if hasattr(db_user, 'language'):
                    db_user.language = lang
                    db.commit()
                    
                    if lang == 'am':
                        msg = "✅ ቋንቋ ወደ አማርኛ ተቀይሯል!"
                    else:
                        msg = "✅ Language changed to English!"
                    
                    await query.answer(msg, show_alert=True)
                    await query.edit_message_text(
                        msg + "\n\nUse /start to see changes.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Settings", callback_data="settings")]])
                    )
                else:
                    await query.answer("⚠️ Update database first", show_alert=True)
        finally:
            db.close()

    async def moderation_queue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        db = SessionLocal()
        try:
            pending = db.query(ContentModeration).filter(
                ContentModeration.status == 'pending'
            ).order_by(ContentModeration.moderated_at.desc()).limit(10).all()
            
            if not pending:
                await update.message.reply_text("✅ No pending content to moderate")
                return
            
            text = f"🔍 Content Moderation Queue ({len(pending)} pending)\n\n"
            for mod in pending:
                content = db.query(Content).filter(Content.id == mod.content_id).first()
                if content:
                    text += f"ID: {mod.id}\n📝 {content.title[:50]}...\n🔗 {content.url}\n\n"
            
            text += "Commands:\n/approve_content <id>\n/reject_content <id> <reason>"
            await update.message.reply_text(text)
        finally:
            db.close()
    
    async def approve_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /approve_content <moderation_id>")
            return
        
        db = SessionLocal()
        try:
            mod_id = int(context.args[0])
            mod = db.query(ContentModeration).filter(ContentModeration.id == mod_id).first()
            
            if not mod:
                await update.message.reply_text("❌ Moderation entry not found")
                return
            
            mod.status = 'approved'
            mod.moderated_by = self.admin_id
            mod.moderated_at = datetime.now(timezone.utc)
            db.commit()
            
            await update.message.reply_text(f"✅ Content {mod_id} approved")
        finally:
            db.close()
    
    async def reject_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /reject_content <moderation_id> <reason>")
            return
        
        db = SessionLocal()
        try:
            mod_id = int(context.args[0])
            reason = ' '.join(context.args[1:])
            
            mod = db.query(ContentModeration).filter(ContentModeration.id == mod_id).first()
            
            if not mod:
                await update.message.reply_text("❌ Moderation entry not found")
                return
            
            mod.status = 'rejected'
            mod.reason = reason
            mod.moderated_by = self.admin_id
            mod.moderated_at = datetime.now(timezone.utc)
            db.commit()
            
            await update.message.reply_text(f"❌ Content {mod_id} rejected: {reason}")
        finally:
            db.close()
