# Bulk User Operations Guide

## ✅ Features

Perform operations on multiple users at once:

- **Bulk Grant Pro** - Give pro access to multiple users
- **Bulk Revoke Pro** - Remove pro from multiple users
- **Bulk Messaging** - Send messages to multiple users
- **Message Inactive Users** - Re-engage inactive users
- **Message Expiring Subs** - Remind users to renew
- **Export Users** - Export user data to CSV
- **Bulk Statistics** - View user metrics
- **Bulk Delete** - Remove inactive users

## 🚀 Quick Start

### Admin Commands

All commands require admin privileges (set in `ADMIN_USER_ID`).

### 1. Grant Pro to Multiple Users

```
/bulk_grant 123456,789012,345678 30
```

- Grants 30 days of pro access
- Separate user IDs with commas (no spaces)
- Shows success/failure count

### 2. Revoke Pro from Multiple Users

```
/bulk_revoke 123456,789012,345678
```

- Removes pro access immediately
- Useful for expired trials or violations

### 3. Message Multiple Users

```
/bulk_message 123456,789012 Hello everyone! Check out our new features.
```

- Sends custom message to specified users
- Rate-limited to avoid Telegram restrictions

### 4. Message Inactive Users

```
/message_inactive 30
```

- Finds users inactive for 30+ days
- Sends re-engagement message
- Default message: "We miss you! Come back..."

### 5. Export Users to CSV

```
/export_users
```

- Exports all users to CSV file
- Includes: ID, username, pro status, dates
- Sends file in chat

### 6. View Bulk Statistics

```
/bulk_stats
```

Shows:
- Total users
- Pro vs Free users
- Active users (7 days)
- Expiring subscriptions
- Inactive users (30 days)
- Conversion rate

## 📋 Advanced Usage

### Python Script Usage

```python
from bulk_operations import get_bulk_ops

# Initialize
bulk_ops = get_bulk_ops()

# Get inactive users
inactive = bulk_ops.get_inactive_users(days=30)
print(f"Found {len(inactive)} inactive users")

# Grant pro to specific users
results = bulk_ops.bulk_grant_pro([123456, 789012], days=30)
print(f"Success: {results['success']}, Failed: {results['failed']}")

# Export users
result = bulk_ops.export_users_csv('my_users.csv')
print(f"Exported {result['exported']} users")

# Close connection
bulk_ops.close()
```

### Query Users by Criteria

```python
# Get users created after specific date
from datetime import datetime, timezone
users = bulk_ops.get_users_by_criteria({
    'created_at': {'after': datetime(2024, 1, 1, tzinfo=timezone.utc)}
})

# Get pro users
pro_users = bulk_ops.get_pro_users()

# Get users with expiring subscriptions (7 days)
expiring = bulk_ops.get_expiring_subscriptions(days=7)

# Get active users (minimum 10 views)
active = bulk_ops.get_users_by_activity(min_views=10)
```

### Bulk Operations

```python
# Grant pro to multiple users
results = bulk_ops.bulk_grant_pro(
    user_ids=[123, 456, 789],
    days=30
)

# Extend subscriptions
results = bulk_ops.bulk_extend_subscription(
    user_ids=[123, 456],
    days=7  # Add 7 more days
)

# Ban multiple users
results = bulk_ops.bulk_ban_users(
    user_ids=[123, 456],
    reason="Spam"
)

# Unban users
results = bulk_ops.bulk_unban_users([123, 456])
```

### Messaging Operations

```python
import asyncio

# Message specific users
results = await bulk_ops.bulk_message_users(
    user_ids=[123, 456, 789],
    message="🎉 New feature released!",
    delay=0.05  # 50ms between messages
)

# Message inactive users
results = await bulk_ops.message_inactive_users(
    days=30,
    message="We miss you! Come back for new content.",
    delay=0.05
)

# Message expiring subscriptions
results = await bulk_ops.message_expiring_subscriptions(
    days=7,
    message="⚠️ Your subscription expires in 7 days!",
    delay=0.05
)

# Message all free users
results = await bulk_ops.message_free_users(
    message="🎁 Special offer: 50% off Pro!",
    delay=0.05
)

# Message all pro users
results = await bulk_ops.message_pro_users(
    message="✨ Thank you for being a Pro member!",
    delay=0.05
)
```

### Export Operations

```python
# Export all users
result = bulk_ops.export_users_csv('all_users.csv')

# Export users by criteria
result = bulk_ops.export_users_csv(
    filename='pro_users.csv',
    criteria={'is_premium': True}
)

# Export user statistics
result = bulk_ops.export_user_stats('user_stats.csv')
```

### Delete Operations

```python
# Delete inactive users (90+ days)
result = bulk_ops.bulk_delete_inactive_users(days=90)
print(f"Deleted {result['deleted']} users")

# Delete specific users
results = bulk_ops.bulk_delete_users([123, 456, 789])
```

## 📊 Use Cases

### 1. Re-engagement Campaign

```python
# Find inactive users
inactive = bulk_ops.get_inactive_users(days=30)

# Send re-engagement message
message = """
👋 We miss you!

Check out what's new:
• 🎮 Gaming content
• 💻 Tech news
• ⚽ Sports updates

Come back: /start
"""

results = await bulk_ops.bulk_message_users(
    [u.telegram_id for u in inactive],
    message
)
```

### 2. Subscription Renewal Reminders

```python
# Find expiring subscriptions
expiring = bulk_ops.get_expiring_subscriptions(days=7)

# Send renewal reminder
message = """
⚠️ Your Pro subscription expires in 7 days!

Renew now to keep:
✅ Unlimited access
✅ All categories
✅ Ad-free experience

Renew: /subscribe
"""

results = await bulk_ops.bulk_message_users(
    [u.telegram_id for u in expiring],
    message
)
```

### 3. Promotional Campaign

```python
# Target free users
free_users = bulk_ops.get_free_users()

# Send promotion
message = """
🎁 Special Offer: 50% OFF Pro!

Limited time only:
• Was: $5/month
• Now: $2.50/month

Upgrade: /subscribe
"""

results = await bulk_ops.message_free_users(message)
```

### 4. User Cleanup

```python
# Delete users inactive for 90+ days
result = bulk_ops.bulk_delete_inactive_users(days=90)
print(f"Cleaned up {result['deleted']} inactive users")

# Export before deleting (backup)
bulk_ops.export_users_csv('backup_before_cleanup.csv')
```

### 5. Bulk Pro Access (Giveaway)

```python
# Winners of a giveaway
winner_ids = [123456, 789012, 345678]

# Grant 30 days pro
results = bulk_ops.bulk_grant_pro(winner_ids, days=30)

# Notify winners
message = """
🎉 Congratulations!

You won 30 days of Pro access!

Enjoy unlimited features:
✅ All categories
✅ No limits
✅ Premium support

Start exploring: /start
"""

await bulk_ops.bulk_message_users(winner_ids, message)
```

## ⚠️ Important Notes

### Rate Limiting

Telegram has rate limits:
- **30 messages/second** to different users
- **1 message/second** to same user

The system automatically adds delays (50ms default).

### Error Handling

All bulk operations return results:
```python
{
    'success': 10,  # Successful operations
    'failed': 2,    # Failed operations
    'errors': [     # Error details
        'User 123: Not found',
        'User 456: Permission denied'
    ]
}
```

### Data Safety

**Before bulk delete:**
1. Export users first (backup)
2. Test with small batch
3. Verify results
4. Then proceed with full delete

### Performance

- **Small batches** (< 100 users): Instant
- **Medium batches** (100-1000): Few seconds
- **Large batches** (1000+): Few minutes

## 🔐 Security

### Admin Only

All bulk operations require admin privileges:
```python
if update.effective_user.id != self.admin_id:
    return  # Blocked
```

### Audit Trail

Log all bulk operations:
```python
logger.info(f"Admin {admin_id} granted pro to {len(user_ids)} users")
```

### Confirmation

For destructive operations, add confirmation:
```python
confirm = input("Delete 100 users? (yes/no): ")
if confirm.lower() != 'yes':
    print("Cancelled")
    return
```

## 📈 Best Practices

1. **Test First** - Try with 1-2 users before bulk
2. **Export Backup** - Always export before delete
3. **Monitor Results** - Check success/failure counts
4. **Rate Limit** - Don't spam users
5. **Personalize** - Use user data in messages
6. **Track Metrics** - Monitor campaign effectiveness
7. **Clean Regularly** - Remove inactive users monthly

## 🆘 Troubleshooting

**Issue: "User not found"**
- User may have blocked bot
- User ID incorrect
- User deleted account

**Issue: "Failed to send message"**
- User blocked bot
- User privacy settings
- Rate limit exceeded

**Issue: "Permission denied"**
- Not admin user
- Check ADMIN_USER_ID in .env

**Issue: "Database error"**
- Check database connection
- Verify user exists
- Check for locked tables

## 📞 Support

For issues:
1. Check error messages
2. Verify admin privileges
3. Test with single user first
4. Check logs for details
5. Contact support if persists

## ✅ Checklist

Before running bulk operations:

- [ ] Verified admin access
- [ ] Tested with 1-2 users
- [ ] Exported backup (if deleting)
- [ ] Prepared message content
- [ ] Checked rate limits
- [ ] Monitored results
- [ ] Logged operation

Your bot now has powerful bulk user management! 🎉
