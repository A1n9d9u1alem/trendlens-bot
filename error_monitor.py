"""
Error Monitoring System
Integrates Sentry for real-time error tracking and monitoring
"""

import os
import logging
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from dotenv import load_dotenv

load_dotenv()


class ErrorMonitor:
    """Centralized error monitoring and tracking"""
    
    def __init__(self):
        self.sentry_enabled = False
        self.sentry_dsn = os.getenv('SENTRY_DSN')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        if self.sentry_dsn:
            self.setup_sentry()
        else:
            self.setup_local_logging()
    
    def setup_sentry(self):
        """Initialize Sentry error tracking"""
        try:
            # Configure Sentry
            sentry_sdk.init(
                dsn=self.sentry_dsn,
                environment=self.environment,
                
                # Set traces_sample_rate to 1.0 to capture 100% of transactions
                traces_sample_rate=1.0 if self.environment == 'development' else 0.1,
                
                # Capture 100% of errors
                sample_rate=1.0,
                
                # Enable performance monitoring
                enable_tracing=True,
                
                # Integrations
                integrations=[
                    LoggingIntegration(
                        level=logging.INFO,
                        event_level=logging.ERROR
                    ),
                    SqlalchemyIntegration(),
                    RedisIntegration(),
                ],
                
                # Release tracking
                release=os.getenv('APP_VERSION', '1.0.0'),
                
                # Additional options
                attach_stacktrace=True,
                send_default_pii=False,  # Don't send personal data
                max_breadcrumbs=50,
                
                # Before send hook to filter sensitive data
                before_send=self.before_send_filter,
            )
            
            self.sentry_enabled = True
            logging.info("✅ Sentry error monitoring enabled")
            
        except Exception as e:
            logging.error(f"❌ Failed to initialize Sentry: {e}")
            self.setup_local_logging()
    
    def setup_local_logging(self):
        """Setup local file logging as fallback"""
        log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'error.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        logging.info("📝 Local file logging enabled")
    
    def before_send_filter(self, event, hint):
        """Filter sensitive data before sending to Sentry"""
        # Remove sensitive environment variables
        if 'extra' in event:
            sensitive_keys = ['DATABASE_URL', 'TELEGRAM_BOT_TOKEN', 'REDIS_URL', 
                            'STRIPE_SECRET_KEY', 'API_KEY', 'PASSWORD']
            
            for key in sensitive_keys:
                if key in event['extra']:
                    event['extra'][key] = '[FILTERED]'
        
        return event
    
    def capture_exception(self, error, context=None):
        """Capture and report exception"""
        if self.sentry_enabled:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                sentry_sdk.capture_exception(error)
        else:
            logging.error(f"Exception: {error}", exc_info=True)
    
    def capture_message(self, message, level='info', context=None):
        """Capture custom message"""
        if self.sentry_enabled:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                sentry_sdk.capture_message(message, level=level)
        else:
            log_func = getattr(logging, level, logging.info)
            log_func(message)
    
    def set_user(self, user_id, username=None, email=None):
        """Set user context for error tracking"""
        if self.sentry_enabled:
            sentry_sdk.set_user({
                "id": user_id,
                "username": username,
                "email": email
            })
    
    def add_breadcrumb(self, message, category='default', level='info', data=None):
        """Add breadcrumb for debugging"""
        if self.sentry_enabled:
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                level=level,
                data=data or {}
            )
    
    def start_transaction(self, name, op='task'):
        """Start performance transaction"""
        if self.sentry_enabled:
            return sentry_sdk.start_transaction(name=name, op=op)
        return None


# Global error monitor instance
error_monitor = ErrorMonitor()


def monitor_errors(func):
    """Decorator to monitor function errors"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_monitor.capture_exception(e, context={
                'function': func.__name__,
                'args': str(args)[:200],
                'kwargs': str(kwargs)[:200]
            })
            raise
    return wrapper


async def async_monitor_errors(func):
    """Decorator for async functions"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_monitor.capture_exception(e, context={
                'function': func.__name__,
                'args': str(args)[:200],
                'kwargs': str(kwargs)[:200]
            })
            raise
    return wrapper
