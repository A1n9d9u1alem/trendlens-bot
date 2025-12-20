# Deployment Guide

## What's Already Deployed
✅ PostgreSQL - Supabase (online)
✅ Redis - Upstash/Redis Cloud (online)

## What Needs Deployment

### 1. Telegram Bot (bot.py)
**Options:**
- **Railway** (Recommended) - Free tier, easy Python deployment
- **Render** - Free tier with auto-sleep
- **Heroku** - Paid ($5/month minimum)
- **PythonAnywhere** - Free tier available
- **AWS EC2** - Free tier 12 months
- **DigitalOcean** - $4/month droplet

### 2. Content Aggregator (aggregator.js)
**Options:**
- **Railway** - Same as bot
- **Render** - Free tier
- **Vercel** - Free for serverless
- **Heroku** - Paid
- **Same server as bot** - Run both together

## Quick Deploy: Railway (Recommended)

### Deploy Bot to Railway:
1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Add environment variables from .env
6. Railway auto-detects Python and deploys

### Deploy Aggregator to Railway:
1. Create another service in same project
2. Point to same repo
3. Set start command: `node aggregator.js`
4. Add same environment variables

## Alternative: Single Server Deployment

### Using a VPS (DigitalOcean/AWS):
```bash
# Install dependencies
sudo apt update
sudo apt install python3-pip nodejs npm

# Clone repo
git clone <your-repo>
cd telegram-bot-4

# Install Python packages
pip3 install -r requirements.txt

# Install Node packages
npm install

# Run with PM2 (process manager)
npm install -g pm2
pm2 start aggregator.js
pm2 start bot.py --interpreter python3
pm2 save
pm2 startup
```

## Environment Variables Needed:
- TELEGRAM_BOT_TOKEN
- ADMIN_USER_ID
- DATABASE_URL (Supabase connection string)
- REDIS_URL (Upstash connection string)
- REDDIT_CLIENT_ID
- REDDIT_CLIENT_SECRET
- YOUTUBE_API_KEY
- TWITTER_BEARER_TOKEN
- NEWS_API_KEY

## Keep Bot Running 24/7:
- Railway/Render: Automatic
- VPS: Use PM2 or systemd
- PythonAnywhere: Always-on task (paid)

## Cost Estimate:
- **Free Option**: Railway (bot) + Railway (aggregator) + Supabase + Upstash = $0/month
- **Paid Option**: Single VPS ($4-5/month) runs everything
