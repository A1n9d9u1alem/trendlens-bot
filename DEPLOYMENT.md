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




I'll help you complete deploying both services to Railway. Let me break this down into clear steps.

Searched docs: deploy multiple services same repository Railway × 2
Here's the step-by-step guide to complete your deployment:

Deploy Bot (Python) - Already Done
You've completed this. Railway auto-detected Python and deployed it.

Deploy Aggregator (Node.js) - Complete These Steps
Step 1: Create a New Service
Go to your Railway project dashboard
Click "New" button (top right)
Select "Service" → "GitHub Repo"
Select the same repository you used for the Bot
Step 2: Configure the Aggregator Service
Once the service is created, go to its Settings
Under "Deploy" section, find "Start Command"
Set it to: node aggregator.js
Save changes
Step 3: Add Environment Variables
Go to the Aggregator service's "Variables" tab
Add all the same environment variables from your .env file:
Click "New Variable"
Enter the variable name (e.g., API_KEY)
Enter the value
Repeat for each variable
Make sure both services have identical environment variables
Step 4: Deploy
Railway will automatically detect the changes
The Aggregator service will build and deploy
Monitor the deployment in the "Deployments" tab
Step 5: Verify Both Services
Check both services are running (green status)
View logs to confirm no errors
Test your Bot and Aggregator endpoints
Key Points:

Both services share the same repo but run different entry points
Environment variables are per-service (set them on both)
Railway handles the Node.js build automatically
You can view logs for each service independently
Need help with any specific step?