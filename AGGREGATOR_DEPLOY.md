# Deploy Aggregator to Railway - Step by Step

## 🎯 Quick Deploy Guide

### Step 1: In Railway Dashboard

1. Go to your Railway project
2. Click **"New Service"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `trendlens-bot` repository

### Step 2: Configure Aggregator Service

1. Click on the new service (it will auto-detect Node.js)
2. Go to **Settings** tab
3. Find **"Start Command"**
4. Enter: `node aggregator.js`
5. Click **Save**

### Step 3: Add Environment Variables

Click **Variables** tab and add these:

```
DATABASE_URL=postgresql://postgres.esldxlaldfxtinbkfrkg:F3ItjUmy8nllJ9uR@aws-1-eu-west-1.pooler.supabase.com:5432/postgres

REDIS_URL=redis://default:AWMLAAIncDE5N2UxODc0ZDRkNmY0Mjk5YTZjNmQxZTg2ZDA5YTE0NXAxMjUzNTU@unified-hare-25355.upstash.io:6379

YOUTUBE_API_KEY=AIzaSyBY8eF9TQPCX5cq-mX6OJ0Jjy9sEeFUjts

TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAHmm4wEAAAAAbUAnlfyrsgdtiwEUhlZsf4gLTDs%3D9czFsciROicLZKpMefhc8u4HNmGND9HTFhyuHq9dVeiD7lNE7y

NEWS_API_KEY=15bd382330a64d0fadae794b55dac716

TIKTOK_SCRAPE_ENABLED=true

TIKTOK_REQUEST_TIMEOUT=10000
```

### Step 4: Deploy

1. Railway will automatically deploy
2. Wait for deployment to complete
3. Status should show **"Online"**

### Step 5: Check Logs

1. Click **Deployments** tab
2. Click latest deployment
3. View logs - should see:
   - "Aggregator initialized"
   - "Redis connected"
   - "Fetching memes..."
   - "Content aggregation completed"

## ✅ Success Indicators

- Service status: **Online** ✓
- Logs show periodic fetching ✓
- No error messages ✓
- Supabase content table filling up ✓

## 🐛 If It Fails

**Check logs for:**
- Database connection errors → Verify DATABASE_URL
- Redis errors → Verify REDIS_URL
- API errors → Check API keys
- Module errors → Railway should auto-install packages

**Common fixes:**
- Redeploy the service
- Check all environment variables are set
- Verify package.json exists
- Check Node.js version compatibility

## 🎉 Done!

Your aggregator is now running 24/7 fetching trending content!
