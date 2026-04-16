"""
Error Recovery System
Provides retry logic, fallback mechanisms, and graceful degradation
"""

import logging
import asyncio
from functools import wraps
from typing import Callable, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorRecovery:
    """Handles error recovery with retry and fallback strategies"""
    
    @staticmethod
    def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
        """Decorator for retrying failed operations with exponential backoff"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                            await asyncio.sleep(delay)
                        else:
                            logger.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
                
                raise last_error
            return wrapper
        return decorator
    
    @staticmethod
    def with_fallback(fallback_value: Any = None):
        """Decorator that returns fallback value on error"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"{func.__name__} failed, using fallback: {e}")
                    return fallback_value
            return wrapper
        return decorator
    
    @staticmethod
    async def safe_db_operation(operation: Callable, fallback: Any = None) -> Tuple[bool, Any]:
        """Execute database operation with error recovery"""
        try:
            result = await operation()
            return True, result
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            return False, fallback
    
    @staticmethod
    async def safe_api_call(api_func: Callable, *args, **kwargs) -> Optional[Any]:
        """Execute API call with timeout and error handling"""
        try:
            return await asyncio.wait_for(api_func(*args, **kwargs), timeout=10.0)
        except asyncio.TimeoutError:
            logger.error(f"API call {api_func.__name__} timed out")
            return None
        except Exception as e:
            logger.error(f"API call {api_func.__name__} failed: {e}")
            return None
