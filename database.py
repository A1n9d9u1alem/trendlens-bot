from sqlalchemy import create_engine, Column, Integer, BigInteger, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

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
engine = create_engine(
    os.getenv('DATABASE_URL'),
    pool_size=10,              # Reduced from 20
    max_overflow=20,           # Reduced from 40
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=30,
    echo=False,
    connect_args={
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000'
    },
    pool_use_lifo=True,        # Use LIFO for better connection reuse
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def get_db_context():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class NotificationLog(Base):
    __tablename__ = 'notification_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    content_id = Column(Integer, ForeignKey('content.id'))
    status = Column(String(20), default='pending')  # pending, sent, failed
    sent_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
