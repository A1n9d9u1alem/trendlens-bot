# Error Monitoring Setup Guide

## ✅ What's Included

- **Sentry Integration** - Real-time error tracking
- **Local Logging** - Fallback file-based logging
- **Error Context** - Detailed error information
- **User Tracking** - Associate errors with users
- **Performance Monitoring** - Track slow operations
- **Breadcrumbs** - Debug trail for errors

## 🚀 Quick Setup

### Option 1: Sentry (Recommended for Production)

**1. Create Sentry Account:**
- Go to https://sentry.io/signup/
- Create free account (50k errors/month free)

**2. Create New Project:**
- Click "Create Project"
- Select "Python" as platform
- Name it "TrendLens Bot"
- Copy the DSN (looks like: `https://xxx@xxx.ingest.sentry.io/xxx`)

**3. Add to .env:**
```env
# Error Monitoring
SENTRY_DSN=https://your-dsn-here@sentry.io/project-id
ENVIRONMENT=production
APP_VERSION=1.0.0
```

**4. Install & Run:**
```bash
pip install sentry-sdk
python bot.py
```

✅ **Done!** Errors are now tracked in Sentry dashboard.

### Option 2: Local Logging (Development)

If you don't add `SENTRY_DSN`, the bot automatically uses local file logging:

```bash
# No setup needed - just run
python bot.py
```

Errors saved to: `logs/error.log`

## 📊 Sentry Dashboard

After setup, view errors at: https://sentry.io/organizations/your-org/issues/

**Features:**
- Real-time error alerts
- Stack traces with code context
- User impact tracking
- Error frequency graphs
- Performance monitoring
- Release tracking

## 🔍 Error Tracking Features

### 1. Automatic Error Capture
All unhandled exceptions are automatically captured:
```python
# Errors in any command are tracked
@check_ban
async def start(self, update, context):
    # Any error here is captured
    result = 1 / 0  # Captured!
```

### 2. Manual Error Capture
```python
from error_monitor import error_monitor

try:
    risky_operation()
except Exception as e:
    error_monitor.capture_exception(e, context={
        'user_id': user.id,
        'operation': 'payment'
    })
```

### 3. Custom Messages
```python
error_monitor.capture_message(
    "Payment processing slow",
    level='warning',
    context={'duration': 5.2}
)
```

### 4. User Context
```python
error_monitor.set_user(
    user_id=user.id,
    username=user.username
)
```

### 5. Breadcrumbs
```python
error_monitor.add_breadcrumb(
    message="User clicked subscribe",
    category="user_action",
    data={'plan': 'pro'}
)
```

### 6. Performance Tracking
```python
transaction = error_monitor.start_transaction(
    name="process_payment",
    op="payment"
)

# Do work...

if transaction:
    transaction.finish()
```

## 📝 Log Files

When using local logging, files are saved to `logs/`:

```
logs/
├── error.log       # All errors
├── info.log        # Info messages
└── debug.log       # Debug info
```

View logs:
```bash
# Windows
type logs\error.log

# Linux/Mac
tail -f logs/error.log
```

## 🔔 Alerts & Notifications

### Sentry Alerts:

**1. Email Alerts:**
- Go to Sentry → Settings → Alerts
- Create alert rule
- Set conditions (e.g., "New error occurs")
- Add email notification

**2. Slack Integration:**
- Settings → Integrations → Slack
- Connect workspace
- Choose channel for alerts

**3. Discord Webhook:**
- Settings → Integrations → Webhooks
- Add Discord webhook URL
- Get instant error notifications

### Custom Alerts:
```python
# Send to admin on critical error
if critical_error:
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🚨 Critical Error: {error}"
    )
```

## 📈 Monitoring Best Practices

### 1. Set Release Versions
Update `APP_VERSION` in .env when deploying:
```env
APP_VERSION=1.0.1
```

This helps track which version has errors.

### 2. Filter Sensitive Data
Already configured to filter:
- Database URLs
- API keys
- Passwords
- Tokens

### 3. Set Error Sampling
For high-traffic bots, adjust in `error_monitor.py`:
```python
traces_sample_rate=0.1  # Sample 10% of transactions
```

### 4. Monitor Performance
Track slow operations:
```python
with error_monitor.start_transaction(name="fetch_content"):
    contents = fetch_trending_content()
```

### 5. Regular Review
- Check Sentry dashboard daily
- Fix high-frequency errors first
- Monitor error trends

## 🐛 Common Errors to Monitor

**1. Database Errors:**
- Connection timeouts
- Query failures
- Pool exhaustion

**2. API Errors:**
- Rate limits
- Timeouts
- Invalid responses

**3. User Errors:**
- Invalid input
- Permission issues
- Rate limiting

**4. System Errors:**
- Memory issues
- Disk space
- Network problems

## 🔧 Troubleshooting

**Sentry not capturing errors:**
```bash
# Test Sentry connection
python -c "from error_monitor import error_monitor; error_monitor.capture_message('Test')"
```

**Check Sentry status:**
```python
from error_monitor import error_monitor
print(f"Sentry enabled: {error_monitor.sentry_enabled}")
```

**View local logs:**
```bash
# Check if logs directory exists
ls logs/

# View recent errors
tail -20 logs/error.log
```

## 📊 Metrics to Track

Monitor these in Sentry:

1. **Error Rate** - Errors per hour
2. **User Impact** - Users affected by errors
3. **Response Time** - API/database latency
4. **Error Types** - Most common errors
5. **Release Health** - Errors by version

## 🆘 Emergency Response

When critical error occurs:

**1. Check Sentry Dashboard:**
- View error details
- Check affected users
- Review stack trace

**2. Quick Fix:**
```bash
# Rollback to previous version
git checkout v1.0.0
python bot.py
```

**3. Notify Users:**
```python
# Broadcast maintenance message
/broadcast System maintenance in progress
```

**4. Fix & Deploy:**
```bash
# Fix issue
git commit -m "Fix critical error"
git push

# Deploy
# (Railway/Heroku auto-deploys)
```

## 💰 Sentry Pricing

**Free Tier:**
- 50,000 errors/month
- 10,000 performance units
- 30-day retention
- Perfect for small bots

**Paid Plans:**
- Team: $26/month
- Business: $80/month
- Enterprise: Custom

For most bots, **free tier is enough**.

## 🔐 Security

**Data Privacy:**
- PII filtering enabled
- Sensitive data removed
- IP addresses anonymized
- Compliant with GDPR

**Access Control:**
- Invite team members
- Role-based permissions
- Audit logs

## 📚 Additional Resources

- Sentry Docs: https://docs.sentry.io/
- Python SDK: https://docs.sentry.io/platforms/python/
- Best Practices: https://docs.sentry.io/product/best-practices/

## ✅ Verification

Test error monitoring:

```bash
# Run bot
python bot.py

# Trigger test error (in another terminal)
python -c "
from error_monitor import error_monitor
error_monitor.capture_message('Test error monitoring', level='error')
print('✅ Test error sent!')
"
```

Check Sentry dashboard - you should see the test error!

## 🎯 Next Steps

1. ✅ Install Sentry SDK: `pip install sentry-sdk`
2. ✅ Add SENTRY_DSN to .env
3. ✅ Run bot and verify in Sentry dashboard
4. ✅ Set up email/Slack alerts
5. ✅ Monitor errors daily
6. ✅ Fix high-priority issues

Your bot now has professional error monitoring! 🎉
