# TrendLens AI - Telegram Social Media Trend Aggregation Bot

A sophisticated Telegram bot that aggregates trending content from Reddit, YouTube, Twitter, TikTok, Instagram, and news sources.

## Architecture

- **Python**: Telegram bot logic, user interactions, subscription management
- **Node.js**: Content aggregation from multiple platforms
- **PostgreSQL**: User data, content storage, analytics
- **Redis**: Caching trending content, rate limiting

## Features

### Free Tier
- 10 requests/day
- Top 5 trends per category
- 3 categories access
- Text + links only

### Pro Tier ($4.99/month or $49.99/year)
- Unlimited requests
- Top 20+ trends per category
- All categories
- Rich media previews
- Real-time updates
- Ad-free experience
- Save & bookmark content

## Setup

### 1. Install Dependencies

**Python:**
```bash
pip install -r requirements.txt
```

**Node.js:**
```bash
npm install
```

### 2. Configure Environment

Edit `.env` file with your API keys:
- Telegram Bot Token (from @BotFather)
- Reddit API credentials
- YouTube API key
- Twitter Bearer Token
- News API key
- Database URL
- Redis URL

### 3. Setup Online Databases (No Local Install Needed!)

**PostgreSQL (Choose one):**
- **Supabase** (Recommended): https://supabase.com - 500 MB free
- **ElephantSQL**: https://elephantsql.com - 20 MB free
- **Aiven**: https://aiven.io - 1 GB (30-day trial)

**Redis (Choose one):**
- **Upstash** (Recommended): https://upstash.com - 10k commands/day free
- **Redis Cloud**: https://redis.com/try-free/ - 30 MB free

See `ONLINE_DATABASE_SETUP.md` for detailed setup instructions.

**Initialize database:**
```bash
python init_db.py
```

### 4. Start Services

**Terminal 1 - Content Aggregator:**
```bash
node aggregator.js
```

**Terminal 2 - Telegram Bot:**
```bash
python bot.py
```

## Bot Commands

- `/start` - Welcome & onboarding
- `/categories` - Browse categories
- `/trending [category]` - Get trending content
- `/subscribe` - Upgrade to Pro
- `/settings` - Manage preferences

## API Keys Setup

### Reddit
1. Go to https://www.reddit.com/prefs/apps
2. Create an app (script type)
3. Copy client ID and secret

### YouTube
1. Go to Google Cloud Console
2. Enable YouTube Data API v3
3. Create API key

### Twitter
1. Go to https://developer.twitter.com
2. Create app and get Bearer Token

### News API
1. Go to https://newsapi.org
2. Sign up and get API key

## Project Structure

```
telegram bot 4/
├── bot.py              # Main Telegram bot
├── aggregator.js       # Content fetching service
├── database.py         # Database models
├── config.py           # Configuration
├── requirements.txt    # Python dependencies
├── package.json        # Node.js dependencies
├── .env               # Environment variables
└── init_db.sql        # Database schema
```

## Scaling Considerations

- Use Redis for caching and rate limiting
- Implement queue system (Celery/Bull) for heavy operations
- Deploy aggregator and bot separately
- Use CDN for media content
- Implement horizontal scaling with load balancer

## Security

- Store API keys in environment variables
- Validate all user inputs
- Implement rate limiting
- Use HTTPS for webhooks
- Verify payment callbacks

## License

MIT