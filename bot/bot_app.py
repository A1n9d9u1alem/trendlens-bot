"""
TrendLens Bot - Main Application
Modular architecture with separated concerns
"""

import os
import signal
import logging
import asyncio
import redis
from datetime import datetime, timezone
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, InlineQueryHandler
from dotenv import load_dotenv
from typing import Optional, Dict, List, Any
from redis import Redis

# Import handlers and services
from bot.commands.user_commands import UserCommands
from bot.commands.admin_commands import AdminCommands
from bot.commands.payment_commands import PaymentCommands
from bot.commands.admin_user_management import AdminUserManagement
from bot.commands.search_commands import SearchCommands
from bot.commands.content_moderation import ContentModeration
from bot.handlers.callback_handlers import CallbackHandlers
from bot.services.analytics_service import AnalyticsService

# Import existing handlers
from payment_handler import PaymentHandler
from video_handler import VideoHandler
from image_gallery_handler import ImageGalleryHandler
from thumbnail_handler import ThumbnailHandler
from error_monitor import error_monitor

load_dotenv()


class TrendLensBot:
    """Main bot application with modular architecture"""
    
    def __init__(self) -> None:
        # Configuration
        self.token: str = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_id: int = int(os.getenv('ADMIN_USER_ID', '0'))
        
        # Handlers
        self.payment_handler: PaymentHandler = PaymentHandler()
        self.video_handler: VideoHandler = VideoHandler()
        self.gallery_handler: ImageGalleryHandler = ImageGalleryHandler()
        self.thumbnail_handler: ThumbnailHandler = ThumbnailHandler()
        
        # Initialize Redis
        self._init_redis()
        
        # Categories and keywords
        self.categories: List[str] = ['memes', 'sports', 'entertainment', 'gaming', 'tech', 'news', 'jobs']
        
        # Sports leagues
        self.sports_leagues = {
            'premier_league': 'Premier League (England)',
            'la_liga': 'La Liga (Spain)',
            'bundesliga': 'Bundesliga (Germany)',
            'serie_a': 'Serie A (Italy)',
            'ligue_1': 'Ligue 1 (France)',
            'champions_league': 'Champions League',
            'europa_league': 'Europa League',
            'nba': 'NBA (Basketball)',
            'nfl': 'NFL (American Football)',
            'all_sports': 'All Sports'
        }
        
        self.sports_keywords = {
            'premier_league': ['premier league', 'epl', 'manchester united', 'man united', 'liverpool', 'chelsea', 'arsenal', 'manchester city', 'man city', 'tottenham', 'spurs', 'newcastle', 'brighton', 'aston villa', 'west ham', 'everton', 'leicester', 'wolves', 'fulham', 'brentford', 'crystal palace', 'nottingham forest', 'bournemouth', 'luton', 'burnley', 'sheffield united'],
            'la_liga': ['la liga', 'real madrid', 'barcelona', 'barca', 'atletico madrid', 'sevilla', 'real betis', 'villarreal', 'athletic bilbao', 'real sociedad', 'valencia', 'getafe', 'osasuna', 'girona', 'mallorca', 'celta vigo', 'cadiz', 'granada', 'almeria'],
            'bundesliga': ['bundesliga', 'bayern munich', 'bayern', 'borussia dortmund', 'dortmund', 'bvb', 'rb leipzig', 'leipzig', 'union berlin', 'freiburg', 'bayer leverkusen', 'leverkusen', 'eintracht frankfurt', 'wolfsburg', 'hoffenheim', 'borussia monchengladbach', 'mainz', 'cologne', 'augsburg', 'stuttgart', 'bochum', 'heidenheim', 'darmstadt'],
            'serie_a': ['serie a', 'juventus', 'juve', 'inter milan', 'inter', 'ac milan', 'milan', 'roma', 'napoli', 'lazio', 'atalanta', 'fiorentina', 'torino', 'bologna', 'monza', 'udinese', 'sassuolo', 'empoli', 'verona', 'lecce', 'cagliari', 'frosinone', 'salernitana'],
            'ligue_1': ['ligue 1', 'psg', 'paris saint-germain', 'paris saint germain', 'marseille', 'lyon', 'monaco', 'lille', 'nice', 'lens', 'rennes', 'reims', 'toulouse', 'montpellier', 'strasbourg', 'brest', 'nantes', 'lorient', 'le havre', 'metz', 'clermont'],
            'champions_league': ['champions league', 'ucl', 'uefa champions', 'champions league final', 'ucl final', 'round of 16', 'quarter final', 'semi final'],
            'europa_league': ['europa league', 'uel', 'uefa europa', 'europa league final', 'conference league'],
            'nba': ['nba', 'basketball', 'lakers', 'warriors', 'celtics', 'lebron', 'curry', 'stephen curry', 'lebron james', 'bucks', 'heat', 'nuggets', 'suns', 'clippers', 'mavericks', 'nets', 'sixers', 'knicks', 'bulls', 'raptors', 'grizzlies', 'pelicans', 'kings', 'hawks', 'cavaliers', 'pacers', 'magic', 'hornets', 'pistons', 'rockets', 'spurs', 'thunder', 'trail blazers', 'jazz', 'timberwolves', 'wizards'],
            'nfl': ['nfl', 'american football', 'super bowl', 'patriots', 'chiefs', 'cowboys', 'packers', 'steelers', '49ers', 'eagles', 'ravens', 'bills', 'bengals', 'dolphins', 'chargers', 'raiders', 'broncos', 'colts', 'titans', 'jaguars', 'texans', 'browns', 'saints', 'buccaneers', 'falcons', 'panthers', 'rams', 'seahawks', 'cardinals', 'vikings', 'lions', 'bears', 'giants', 'commanders', 'mahomes', 'brady', 'josh allen'],
            'all_sports': ['football', 'soccer', 'basketball', 'sports', 'goal', 'match', 'game', 'player', 'team', 'league', 'tournament', 'championship']
        }
        
        self.tech_subcategories = {
            'ai_data': 'Artificial Intelligence & Data',
            'software': 'Software, Web & App Development', 
            'cyber': 'Cyber, Cloud & Networking',
            'hardware': 'Hardware, Robotics & Automation',
            'emerging': 'Emerging & Industry Technologies'
        }
        self.tech_keywords = {
            'ai_data': ['artificial intelligence', 'machine learning', 'deep learning', 'neural network', 'data science', 'data analytics', 'big data', 'chatgpt', 'openai', 'llm', 'generative ai', 'computer vision', 'nlp', 'natural language'],
            'software': ['programming', 'coding', 'developer', 'web development', 'app development', 'javascript', 'python', 'react', 'node.js', 'frontend', 'backend', 'full stack', 'software engineer', 'github', 'git', 'api', 'framework'],
            'cyber': ['cybersecurity', 'security', 'hacking', 'vulnerability', 'encryption', 'cloud computing', 'aws', 'azure', 'google cloud', 'devops', 'kubernetes', 'docker', 'networking', 'firewall', 'vpn', 'penetration test'],
            'hardware': ['hardware', 'robotics', 'robot', 'automation', 'iot', 'internet of things', 'raspberry pi', 'arduino', 'sensor', 'embedded', 'microcontroller', 'circuit', 'electronics', '3d printing'],
            'emerging': ['blockchain', 'cryptocurrency', 'bitcoin', 'ethereum', 'nft', 'web3', 'metaverse', 'virtual reality', 'augmented reality', 'vr', 'ar', 'quantum computing', 'quantum', '5g', '6g']
        }
        self.category_keywords = {
            'memes': ['meme', 'funny', 'humor', 'joke', 'lol', 'dank', 'comedy'],
            'sports': ['football', 'basketball', 'soccer', 'nba', 'nfl', 'sport'],
            'entertainment': ['dance', 'music', 'celebrity', 'movie', 'tv', 'show'],
            'gaming': ['game', 'gaming', 'esports', 'nintendo', 'xbox', 'playstation'],
            'tech': ['technology', 'software', 'ai', 'programming', 'computer'],
            'news': ['news', 'breaking', 'politics', 'world', 'update'],
            'jobs': ['freelance', 'remote', 'hiring', 'upwork', 'fiverr']
        }
        
        # Rate limiting
        self.admin_rate_limit: Dict[str, List[datetime]] = {}
        self.blocked_keywords: List[str] = ['porn', 'xxx', 'sex', 'nude', 'nsfw', 'gore', 'violence']
        
        # Application instance
        self.application: Optional[Application] = None
        self.redis: Optional[Redis] = None
        
        # Initialize command handlers
        self.user_commands = UserCommands(self)
        self.admin_commands = AdminCommands(self)
        self.payment_commands = PaymentCommands(self)
        self.admin_user_mgmt = AdminUserManagement(self)
        self.search_commands = SearchCommands(self)
        self.content_moderation = ContentModeration(self)
        self.callback_handlers = CallbackHandlers(self)
        self.analytics_service = AnalyticsService(self)
        
        # Initialize realtime updates
        from bot.services.realtime_updates import RealtimeUpdates
        self.realtime_updates = RealtimeUpdates(self)
    
    def _init_redis(self) -> None:
        """Initialize Redis connection"""
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
    
    # Utility methods
    def sanitize_input(self, text: str, max_length: int = 200) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        import re
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(text))
        return text[:max_length].strip()
    
    def validate_payment_reference(self, reference: str) -> bool:
        """Validate payment reference format"""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]{5,100}$', reference):
            return False
        return True
    
    def check_admin_rate_limit(self, user_id: int, command: str, max_per_minute: int = 10) -> bool:
        """Rate limit admin commands"""
        now = datetime.now(timezone.utc)
        key = f"{user_id}_{command}"
        
        if key not in self.admin_rate_limit:
            self.admin_rate_limit[key] = []
        
        self.admin_rate_limit[key] = [
            t for t in self.admin_rate_limit[key] 
            if (now - t).total_seconds() < 60
        ]
        
        if len(self.admin_rate_limit[key]) >= max_per_minute:
            return False
        
        self.admin_rate_limit[key].append(now)
        return True
    
    async def error_handler(self, update, context):
        """Enhanced error handler with recovery strategies"""
        import traceback
        from telegram.error import NetworkError, TimedOut, RetryAfter, BadRequest
        
        error = context.error
        logging.error(f"Update {update} caused error {error}")
        logging.error(traceback.format_exc())
        
        # Capture error in monitoring
        try:
            error_monitor.capture_exception(error, context={
                'update': str(update)[:500] if update else 'None',
                'user_id': update.effective_user.id if update and update.effective_user else None,
                'error_type': type(error).__name__
            })
        except:
            pass
        
        # Handle specific error types with recovery
        try:
            if isinstance(error, RetryAfter):
                # Rate limited - wait and retry
                await asyncio.sleep(error.retry_after)
                return
            
            if isinstance(error, TimedOut):
                # Timeout - retry once
                logging.warning("Timeout error, will retry automatically")
                return
            
            if isinstance(error, NetworkError):
                # Network issue - log and continue
                logging.error(f"Network error: {error}")
                return
            
            # Send user-friendly message
            if update and update.effective_message:
                error_msg = "⚠️ Something went wrong.\n\n"
                
                if isinstance(error, BadRequest):
                    error_msg += "❌ Invalid request. Please try a different action."
                elif "timeout" in str(error).lower():
                    error_msg += "⏱️ Request timed out. Please try again."
                elif "network" in str(error).lower():
                    error_msg += "🌐 Network issue. Check your connection."
                elif "database" in str(error).lower():
                    error_msg += "💾 Database temporarily unavailable. Retrying..."
                else:
                    error_msg += "🔧 Unexpected error. Please try again."
                
                await update.effective_message.reply_text(error_msg)
        except Exception as e:
            logging.error(f"Error in error_handler: {e}")
    
    def setup_handlers(self, app: Application) -> None:
        """Setup all command and callback handlers"""
        # Error handler
        app.add_error_handler(self.error_handler)
        
        # User commands
        app.add_handler(CommandHandler("start", self.user_commands.start))
        app.add_handler(CommandHandler("account", self.user_commands.account))
        app.add_handler(CommandHandler("saved", self.user_commands.saved))
        app.add_handler(CommandHandler("trending", self.user_commands.trending))
        app.add_handler(CommandHandler("limit", self.user_commands.limit_status))
        app.add_handler(CommandHandler("search", self.search_commands.search))
        app.add_handler(CommandHandler("live_sports", self.user_commands.live_sports))
        app.add_handler(CommandHandler("breaking_news", self.user_commands.breaking_news))
        
        # Payment commands
        app.add_handler(CommandHandler("confirm", self.payment_commands.confirm_payment))
        app.add_handler(CommandHandler("approve", self.payment_commands.approve_payment))
        app.add_handler(CommandHandler("reject", self.payment_commands.reject_payment))
        
        # Admin commands
        app.add_handler(CommandHandler("stats", self.admin_commands.admin_stats))
        app.add_handler(CommandHandler("broadcast", self.admin_commands.broadcast))
        app.add_handler(CommandHandler("users", self.admin_commands.list_users))
        app.add_handler(CommandHandler("bulk_stats", self.admin_commands.bulk_stats))
        app.add_handler(CommandHandler("analytics_report", self.admin_commands.analytics_report))
        app.add_handler(CommandHandler("recalculate_scores", self.admin_commands.recalculate_scores))
        app.add_handler(CommandHandler("quality_report", self.admin_commands.quality_report))
        app.add_handler(CommandHandler("realtime_status", self.admin_commands.realtime_status))
        app.add_handler(CommandHandler("db_pool_status", self.admin_commands.db_pool_status))
        
        # Admin user management commands
        app.add_handler(CommandHandler("grant_pro", self.admin_user_mgmt.grant_pro))
        app.add_handler(CommandHandler("revoke_pro", self.admin_user_mgmt.revoke_pro))
        app.add_handler(CommandHandler("ban_user", self.admin_user_mgmt.ban_user))
        app.add_handler(CommandHandler("unban_user", self.admin_user_mgmt.unban_user))
        app.add_handler(CommandHandler("user_info", self.admin_user_mgmt.user_info))
        
        # Content moderation commands
        app.add_handler(CommandHandler("moderation_queue", self.content_moderation.moderation_queue))
        app.add_handler(CommandHandler("content_stats", self.content_moderation.content_stats))
        
        # Callback handlers
        app.add_handler(CallbackQueryHandler(self.callback_handlers.start_callback, pattern="^start$"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.show_categories, pattern="^categories$"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.show_tech_category, pattern="^techcat_"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.show_league_content, pattern="^league_"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.show_category, pattern="^cat_"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.apply_time_filter, pattern="^filter_"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.navigate, pattern="^nav_"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.saved_navigate, pattern="^saved_nav_"))
        app.add_handler(CallbackQueryHandler(self.search_commands.search_navigate, pattern="^search_nav_"))
        app.add_handler(CallbackQueryHandler(self.search_commands.search_save, pattern="^search_save_"))
        app.add_handler(CallbackQueryHandler(self.search_commands.new_search, pattern="^new_search$"))
        app.add_handler(CallbackQueryHandler(self.content_moderation.approve_content, pattern="^mod_approve_"))
        app.add_handler(CallbackQueryHandler(self.content_moderation.reject_content, pattern="^mod_reject_"))
        app.add_handler(CallbackQueryHandler(self.content_moderation.mod_navigate, pattern="^mod_nav_"))
        app.add_handler(CallbackQueryHandler(self.content_moderation.mod_exit, pattern="^mod_exit$"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.save_content, pattern="^save_"))
        app.add_handler(CallbackQueryHandler(self.payment_commands.subscribe, pattern="^subscribe$"))
        
        # Settings handlers
        app.add_handler(CallbackQueryHandler(self.callback_handlers.settings, pattern="^settings$"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.account_info, pattern="^account_info$"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.view_saved, pattern="^view_saved$"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.my_stats, pattern="^my_stats$"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.notifications_settings, pattern="^notifications_settings$"))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.help_support, pattern="^help_support$"))
    
    def run(self, use_webhook: bool = False) -> None:
        """Run the bot"""
        import sys
        
        # Fix Windows console encoding
        if sys.platform == 'win32':
            os.system('chcp 65001 >nul 2>&1')
        
        logging.basicConfig(level=logging.INFO)
        
        # Build application
        app = Application.builder().token(self.token).build()
        self.application = app
        
        # Setup handlers
        self.setup_handlers(app)
        
        # Set telegram bot for realtime updates
        self.realtime_updates.set_telegram_bot(app.bot)
        
        # Start realtime updates after bot starts
        async def post_init(application):
            await self.realtime_updates.start_realtime_updates()
        
        app.post_init = post_init
        
        # Stop realtime updates on shutdown
        async def post_shutdown(application):
            await self.realtime_updates.stop_realtime_updates()
            # Dispose database connection pool
            from database import dispose_pool
            dispose_pool()
            logger.info("Bot shutdown complete")
        
        app.post_shutdown = post_shutdown
        
        try:
            print("🤖 TrendLens AI Bot started!")
            print(f"👤 Admin ID: {self.admin_id}")
        except UnicodeEncodeError:
            print("TrendLens AI Bot started!")
            print(f"Admin ID: {self.admin_id}")
        
        # Check for webhook mode
        webhook_url = os.getenv('WEBHOOK_URL')
        port = int(os.getenv('PORT', 8443))
        
        if use_webhook and webhook_url:
            print(f"🌐 Running in WEBHOOK mode on port {port}")
            app.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=self.token,
                webhook_url=f"{webhook_url}/{self.token}",
                drop_pending_updates=True
            )
        else:
            print("🔄 Running in POLLING mode")
            app.run_polling(
                drop_pending_updates=True,
                stop_signals=None if sys.platform == 'win32' else (signal.SIGINT, signal.SIGTERM)
            )


def main() -> None:
    """Main entry point"""
    bot = TrendLensBot()
    use_webhook = os.getenv('WEBHOOK_URL') is not None
    bot.run(use_webhook=use_webhook)


if __name__ == '__main__':
    main()
