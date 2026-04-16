"""
Error Recovery Service
Implements retry logic, circuit breakers, and fallback mechanisms
"""

import asyncio
import logging
from functools import wraps
from datetime import datetime, timezone, timedelta
from typing import Callable, Any, Optional, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Will retry after {self.recovery_timeout}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Will retry after {self.recovery_timeout}s"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}' recovered, closing circuit")
        
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker '{self.name}' opened after "
                f"{self.failure_count} failures"
            )
    
    def reset(self):
        """Manually reset circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'last_failure': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'threshold': self.failure_threshold
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class RetryConfig:
    """Configuration for retry logic"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for automatic retry with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function on retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        initial_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    import random
                    delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    
                    if on_retry:
                        on_retry(attempt, delay, e)
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        initial_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    
                    # Add jitter
                    import random
                    delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    
                    if on_retry:
                        on_retry(attempt, delay, e)
                    
                    import time
                    time.sleep(delay)
            
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class ErrorRecoveryService:
    """Centralized error recovery service"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}
    
    def get_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ) -> CircuitBreaker:
        """Get or create circuit breaker"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )
        return self.circuit_breakers[name]
    
    def record_error(self, service: str, error: Exception):
        """Record error for monitoring"""
        self.error_counts[service] = self.error_counts.get(service, 0) + 1
        self.last_errors[service] = datetime.now(timezone.utc)
        logger.error(f"Error in {service}: {error}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            'error_counts': self.error_counts.copy(),
            'last_errors': {
                k: v.isoformat() for k, v in self.last_errors.items()
            },
            'circuit_breakers': {
                name: cb.get_status() 
                for name, cb in self.circuit_breakers.items()
            }
        }
    
    def reset_all_circuits(self):
        """Reset all circuit breakers"""
        for cb in self.circuit_breakers.values():
            cb.reset()
        logger.info("All circuit breakers reset")


# Global error recovery service instance
error_recovery = ErrorRecoveryService()


# Specific retry decorators for common operations

def retry_database_operation(max_attempts: int = 3):
    """Retry decorator for database operations"""
    from sqlalchemy.exc import OperationalError, DatabaseError
    
    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=0.5,
        max_delay=5.0,
        exceptions=(OperationalError, DatabaseError)
    )


def retry_redis_operation(max_attempts: int = 3):
    """Retry decorator for Redis operations"""
    import redis
    
    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=0.2,
        max_delay=2.0,
        exceptions=(redis.ConnectionError, redis.TimeoutError)
    )


def retry_telegram_operation(max_attempts: int = 3):
    """Retry decorator for Telegram API operations"""
    from telegram.error import NetworkError, TimedOut
    
    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=1.0,
        max_delay=10.0,
        exceptions=(NetworkError, TimedOut)
    )


# Fallback mechanisms

class FallbackHandler:
    """Handle fallback scenarios"""
    
    @staticmethod
    def redis_fallback(func: Callable) -> Callable:
        """Fallback to direct DB if Redis fails"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Redis operation failed, using fallback: {e}")
                # Return None or default value to trigger DB fallback
                return None
        return wrapper
    
    @staticmethod
    def default_value_fallback(default: Any):
        """Return default value on error"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Operation failed, using default: {e}")
                    return default
            return wrapper
        return decorator


# Health check utilities

class HealthChecker:
    """Check health of various services"""
    
    @staticmethod
    @retry_database_operation(max_attempts=2)
    def check_database() -> bool:
        """Check database connectivity"""
        from database import SessionLocal
        db = SessionLocal()
        try:
            db.execute("SELECT 1")
            return True
        finally:
            db.close()
    
    @staticmethod
    @retry_redis_operation(max_attempts=2)
    def check_redis(redis_client) -> bool:
        """Check Redis connectivity"""
        if redis_client:
            redis_client.ping()
            return True
        return False
    
    @staticmethod
    def get_health_status(redis_client=None) -> Dict[str, Any]:
        """Get overall health status"""
        health = {
            'database': False,
            'redis': False,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            health['database'] = HealthChecker.check_database()
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        try:
            health['redis'] = HealthChecker.check_redis(redis_client)
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
        
        return health
