from sqlalchemy import create_engine, Column, Integer, BigInteger, String, DateTime, Boolean, Text, Float, ForeignKey, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import QueuePool, NullPool
from datetime import datetime, timezone
import os
import logging
from dotenv import load_dotenv
from contextlib import contextmanager
from typing import Generator

load_dotenv()

logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(50))
    is_premium = Column(Boolean, default=False)
    subscription_end = Column(DateTime)
    categories = Column(Text)  # JSON string of subscribed categories
    language = Column(String(5), default='en')  # User language preference
    notification_enabled = Column(Boolean, default=True)
    notification_frequency = Column(String(20), default='hourly')  # hourly, daily, instant
    notification_categories = Column(Text)  # JSON array of categories to notify
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
class Content(Base):
    __tablename__ = 'content'
    
    id = Column(Integer, primary_key=True)
    platform = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False, unique=True)
    content_hash = Column(String(64), index=True)  # SHA256 hash for deduplication
    thumbnail = Column(Text)
    description = Column(Text)
    engagement_score = Column(Float, default=0)
    trend_score = Column(Float, default=0)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
class UserInteraction(Base):
    __tablename__ = 'interactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    content_id = Column(Integer, ForeignKey('content.id'))
    action = Column(String(20))  # view, save, share
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Analytics(Base):
    __tablename__ = 'analytics'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    event_type = Column(String(50))  # category_view, content_click, search, etc
    category = Column(String(50))
    event_data = Column(Text)  # JSON data (renamed from metadata)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Float, nullable=False)
    reference = Column(String(100))
    status = Column(String(20), default='pending')  # pending, submitted, approved, rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    approved_at = Column(DateTime)

class ContentModeration(Base):
    __tablename__ = 'content_moderation'
    
    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, ForeignKey('content.id'))
    status = Column(String(20), default='pending')  # pending, approved, rejected
    reason = Column(Text)
    moderated_by = Column(Integer)
    moderated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Database setup with optimized connection pooling
DATABASE_URL = os.getenv('DATABASE_URL')

# Connection pool configuration
POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '20'))  # Number of connections to keep open
MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '40'))  # Additional connections when pool is full
POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))  # Seconds to wait for connection
POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))  # Recycle connections after 1 hour

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,           # Use QueuePool for connection pooling
    pool_size=POOL_SIZE,           # Maintain 20 connections in pool
    max_overflow=MAX_OVERFLOW,     # Allow 40 additional connections
    pool_pre_ping=True,            # Verify connections before using
    pool_recycle=POOL_RECYCLE,     # Recycle connections after 1 hour
    pool_timeout=POOL_TIMEOUT,     # Wait 30s for available connection
    pool_use_lifo=True,            # Use LIFO for better connection reuse
    echo=False,                    # Disable SQL logging (set True for debugging)
    connect_args={
        'connect_timeout': 10,     # Connection timeout
        'options': '-c statement_timeout=30000'  # Query timeout (30s)
    },
    execution_options={
        'isolation_level': 'READ COMMITTED'  # Transaction isolation level
    }
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Don't expire objects after commit
)

# Connection pool event listeners for monitoring
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when new connection is created"""
    logger.debug("Database connection established")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log when connection is checked out from pool"""
    logger.debug("Connection checked out from pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log when connection is returned to pool"""
    logger.debug("Connection returned to pool")

@event.listens_for(engine, "close")
def receive_close(dbapi_conn, connection_record):
    """Log when connection is closed"""
    logger.debug("Database connection closed")

@event.listens_for(engine, "invalidate")
def receive_invalidate(dbapi_conn, connection_record, exception):
    """Log when connection is invalidated"""
    logger.warning(f"Connection invalidated: {exception}")

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session (for FastAPI/async)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database sessions with automatic commit/rollback"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()

def get_pool_status() -> dict:
    """Get current connection pool status"""
    pool = engine.pool
    return {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'total_connections': pool.size() + pool.overflow(),
        'available': pool.checkedin(),
        'in_use': pool.checkedout()
    }

def log_pool_status():
    """Log current pool status for monitoring"""
    status = get_pool_status()
    logger.info(
        f"DB Pool Status - "
        f"Size: {status['pool_size']}, "
        f"Available: {status['available']}, "
        f"In Use: {status['in_use']}, "
        f"Overflow: {status['overflow']}"
    )

def dispose_pool():
    """Dispose all connections in the pool (for shutdown)"""
    engine.dispose()
    logger.info("Database connection pool disposed")


class NotificationLog(Base):
    __tablename__ = 'notification_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    content_id = Column(Integer, ForeignKey('content.id'))
    status = Column(String(20), default='pending')  # pending, sent, failed
    sent_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
