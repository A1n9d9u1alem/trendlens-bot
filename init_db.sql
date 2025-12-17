-- Create database
CREATE DATABASE trendlens;

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(50),
    is_premium BOOLEAN DEFAULT FALSE,
    subscription_end TIMESTAMP,
    categories TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Content table with unique constraint on URL
CREATE TABLE content (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    thumbnail TEXT,
    description TEXT,
    engagement_score FLOAT DEFAULT 0,
    trend_score FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Interactions table
CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    content_id INTEGER REFERENCES content(id),
    action VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_content_category ON content(category);
CREATE INDEX idx_content_trend_score ON content(trend_score DESC);
CREATE INDEX idx_content_created_at ON content(created_at DESC);
CREATE INDEX idx_users_telegram_id ON users(telegram_id);