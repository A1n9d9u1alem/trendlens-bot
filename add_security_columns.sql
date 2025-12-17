-- Add security columns to users table
-- Run this in Supabase SQL Editor

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_request TIMESTAMP DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS request_count INTEGER DEFAULT 0;

-- Update existing users
UPDATE users SET is_banned = FALSE WHERE is_banned IS NULL;
UPDATE users SET last_request = NOW() WHERE last_request IS NULL;
UPDATE users SET request_count = 0 WHERE request_count IS NULL;
