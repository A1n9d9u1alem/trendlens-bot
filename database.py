from sqlalchemy import create_engine, Column, Integer, BigInteger, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
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
    created_at = Column(DateTime, default=datetime.utcnow)
    
class Content(Base):
    __tablename__ = 'content'
    
    id = Column(Integer, primary_key=True)
    platform = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False, unique=True)
    thumbnail = Column(Text)
    description = Column(Text)
    engagement_score = Column(Float, default=0)
    trend_score = Column(Float, default=0)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class UserInteraction(Base):
    __tablename__ = 'interactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    content_id = Column(Integer, ForeignKey('content.id'))
    action = Column(String(20))  # view, save, share
    timestamp = Column(DateTime, default=datetime.utcnow)

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Float, nullable=False)
    reference = Column(String(100))
    status = Column(String(20), default='pending')  # pending, submitted, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)

# Database setup
engine = create_engine(os.getenv('DATABASE_URL'))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()