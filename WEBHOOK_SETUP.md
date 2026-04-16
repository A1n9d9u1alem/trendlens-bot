# Webhook Setup Guide

## Why Webhook Mode?

**Polling Mode (Current):**
- Bot constantly asks Telegram "any new messages?"
- Slower response time
- Uses more resources
- Higher latency

**Webhook Mode (Better):**
- Telegram pushes updates to your bot instantly
- Faster response time (instant)
- More efficient
- Lower latency

## Setup Instructions

### 1. Add to .env file:

```env
# Webhook Configuration (optional - leave empty for polling mode)
WEBHOOK_URL=https://yourdomain.com
PORT=8443
```

### 2. Deploy Options:

#### Option A: Railway/Heroku (Recommended)
```bash
# Railway automatically provides HTTPS domain
# Just set in Railway dashboard:
WEBHOOK_URL=https://your-app.railway.app
PORT=8443
```

#### Option B: VPS with Domain + SSL
```bash
# You need:
# 1. Domain name (e.g., bot.yourdomain.com)
# 2. SSL certificate (Let's Encrypt)
# 3. Nginx reverse proxy

# .env
WEBHOOK_URL=https://bot.yourdomain.com
PORT=8443
```

#### Option C: ngrok (Testing Only)
```bash
# Start ngrok
ngrok http 8443

# Copy HTTPS URL to .env
WEBHOOK_URL=https://abc123.ngrok.io
PORT=8443
```

### 3. Run the bot:

```bash
# Automatically detects webhook mode if WEBHOOK_URL is set
python bot.py
```

## Verification

Check if webhook is active:
```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

## Troubleshooting

**Issue:** Webhook not working
- Ensure HTTPS (not HTTP)
- Check port is open (8443, 443, 80, 88)
- Verify SSL certificate is valid
- Check firewall settings

**Issue:** Still using polling
- Verify WEBHOOK_URL is set in .env
- Check bot logs for "Running in WEBHOOK mode"
- Restart the bot

## Performance Comparison

| Feature | Polling | Webhook |
|---------|---------|---------|
| Response Time | 1-3 seconds | Instant |
| Server Load | High | Low |
| Scalability | Limited | Excellent |
| Setup | Easy | Moderate |

## Production Deployment

For production, use webhook mode with:
- Railway/Heroku (easiest)
- VPS with Nginx + SSL
- Cloud providers (AWS, GCP, Azure)

**Never use ngrok in production!**
