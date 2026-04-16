# 👨‍💼 Admin User Management Guide

## ✅ Implemented Commands

All admin user management commands are now available in the new bot!

## 📋 Available Commands

### 1. Grant Pro Membership
```bash
/grant_pro <user_id> [days]
```

**Description**: Grant Pro membership to a user

**Examples**:
```bash
/grant_pro 123456789 30    # Grant Pro for 30 days
/grant_pro 123456789       # Grant Pro for 30 days (default)
/grant_pro 987654321 90    # Grant Pro for 90 days
```

**What happens**:
- ✅ User gets Pro membership
- ✅ Unlimited content access
- ✅ Can save unlimited content
- ✅ Admin gets confirmation
- ✅ User gets notification

**Output**:
```
✅ Pro membership granted!

👤 User ID: 123456789
📅 Duration: 30 days
⏰ Expires: 2024-02-15

User will have unlimited access until expiration.
```

---

### 2. Revoke Pro Membership
```bash
/revoke_pro <user_id>
```

**Description**: Remove Pro membership from a user

**Examples**:
```bash
/revoke_pro 123456789
```

**What happens**:
- ✅ Pro membership removed
- ✅ User returns to Free Tier
- ✅ Limited access restored
- ✅ Admin gets confirmation
- ✅ User gets notification

**Output**:
```
✅ Pro membership revoked!

👤 User ID: 123456789
📊 Status: Free Tier

User now has limited access.
```

---

### 3. Ban User
```bash
/ban_user <user_id> [reason]
```

**Description**: Ban a user from using the bot

**Examples**:
```bash
/ban_user 123456789 Spam
/ban_user 123456789 Abuse
/ban_user 123456789
```

**What happens**:
- ✅ User is banned
- ✅ Cannot use bot anymore
- ✅ All commands blocked
- ✅ Admin gets confirmation
- ✅ User gets notification

**Output**:
```
✅ User banned!

👤 User ID: 123456789
📝 Reason: Spam
⛔ Status: Banned

User cannot use the bot anymore.
```

**Note**: Cannot ban admin user (safety feature)

---

### 4. Unban User
```bash
/unban_user <user_id>
```

**Description**: Remove ban from a user

**Examples**:
```bash
/unban_user 123456789
```

**What happens**:
- ✅ Ban removed
- ✅ User can use bot again
- ✅ Access restored
- ✅ Admin gets confirmation
- ✅ User gets notification

**Output**:
```
✅ User unbanned!

👤 User ID: 123456789
✅ Status: Active

User can now use the bot again.
```

---

### 5. User Info
```bash
/user_info <user_id>
```

**Description**: Get detailed information about a user

**Examples**:
```bash
/user_info 123456789
```

**Output**:
```
👤 User Information

🆔 User ID: 123456789
👤 Username: @johndoe
📊 Status: ✨ Pro Member
🚦 Account: ✅ Active
📅 Joined: 2024-01-15

📈 Statistics:
👁️ Total Views: 245
💾 Total Saves: 18

⏰ Pro Expires: 2024-02-15 (15 days left)
```

---

## 🎯 Common Use Cases

### Scenario 1: User Requests Pro Access
```bash
# User messages you asking for Pro
/user_info 123456789        # Check their info
/grant_pro 123456789 30     # Grant 30 days Pro
```

### Scenario 2: User Abusing Bot
```bash
/user_info 123456789        # Check their activity
/ban_user 123456789 Spam    # Ban them
```

### Scenario 3: User Appeals Ban
```bash
/user_info 123456789        # Review their case
/unban_user 123456789       # Unban if appropriate
```

### Scenario 4: Pro Subscription Issues
```bash
/user_info 123456789        # Check subscription status
/revoke_pro 123456789       # Remove if needed
/grant_pro 123456789 30     # Re-grant if payment confirmed
```

### Scenario 5: Extend Pro Membership
```bash
/user_info 123456789        # Check current expiry
/grant_pro 123456789 60     # Extend for 60 more days
```

---

## 🔒 Security Features

### Admin-Only Access
- ✅ Only admin can use these commands
- ✅ Regular users get "Admin only command!" message
- ✅ Admin ID configured in .env file

### Safety Checks
- ✅ Cannot ban admin user
- ✅ Validates user exists before action
- ✅ Checks current status before changes
- ✅ Prevents duplicate actions

### Notifications
- ✅ Admin always gets confirmation
- ✅ User gets notified of changes
- ✅ Clear status messages
- ✅ Detailed error messages

---

## 📊 User Status Types

### Pro Member (✨)
- Unlimited content access
- Save unlimited content
- No daily limits
- Priority support

### Free Tier (🆓)
- Limited content views
- Basic features
- Daily limits apply
- Standard support

### Banned (⛔)
- Cannot use bot
- All commands blocked
- Must be unbanned to access

### Active (✅)
- Normal account status
- Can use all features
- Based on membership tier

---

## 🛠️ Admin Workflow

### Daily Tasks
```bash
# Check new users
/users

# Review user activity
/user_info <user_id>

# Handle Pro requests
/grant_pro <user_id> 30
```

### Weekly Tasks
```bash
# Check statistics
/stats

# Review Pro expirations
/users  # Check who needs renewal

# Handle abuse reports
/ban_user <user_id> <reason>
```

### Monthly Tasks
```bash
# Bulk statistics
/bulk_stats

# Review banned users
# Consider unbanning if appropriate
/unban_user <user_id>
```

---

## 💡 Pro Tips

### 1. Always Check User Info First
```bash
/user_info 123456789  # Before any action
```

### 2. Use Descriptive Ban Reasons
```bash
/ban_user 123456789 Spam - Posted 50+ messages in 1 hour
```

### 3. Standard Pro Duration
```bash
/grant_pro <user_id> 30   # 30 days is standard
/grant_pro <user_id> 90   # 90 days for special cases
```

### 4. Document Actions
Keep a log of:
- Who you granted Pro to
- Why you banned users
- When you made changes

### 5. Regular Audits
```bash
# Weekly: Check Pro expirations
# Monthly: Review banned users
# Quarterly: Analyze user stats
```

---

## 🐛 Troubleshooting

### "User not found in database"
**Solution**: User hasn't used /start yet. Ask them to start the bot first.

### "User is already banned"
**Solution**: User is already banned. Use /user_info to check status.

### "User is not a Pro member"
**Solution**: User doesn't have Pro. Use /grant_pro to give them access.

### "Admin only command!"
**Solution**: You're not logged in as admin. Check ADMIN_USER_ID in .env

### "Invalid user ID"
**Solution**: User ID must be a number. Get it from /users command.

---

## 📈 Statistics Tracking

### What Gets Tracked
- Total views per user
- Total saves per user
- Join date
- Pro membership status
- Ban status
- Subscription expiration

### How to Use Stats
```bash
# Individual user
/user_info 123456789

# All users
/users

# Bulk statistics
/bulk_stats
```

---

## 🎓 Best Practices

### DO ✅
- Check user info before actions
- Use descriptive ban reasons
- Notify users of changes
- Keep records of actions
- Review bans periodically
- Grant Pro for specific durations

### DON'T ❌
- Ban without reason
- Grant unlimited Pro (use specific days)
- Forget to notify users
- Ban admin user (system prevents this)
- Revoke Pro without checking
- Ignore user appeals

---

## 🚀 Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `/grant_pro` | Give Pro access | `/grant_pro 123 30` |
| `/revoke_pro` | Remove Pro | `/revoke_pro 123` |
| `/ban_user` | Ban user | `/ban_user 123 Spam` |
| `/unban_user` | Unban user | `/unban_user 123` |
| `/user_info` | Get user details | `/user_info 123` |

---

## 📞 Support

If you encounter issues:
1. Check user exists: `/user_info <user_id>`
2. Verify you're admin: Check .env ADMIN_USER_ID
3. Review error message
4. Check logs for details

---

**All admin user management features are now fully implemented!** 🎉

You have complete control over:
- ✅ Pro memberships
- ✅ User bans
- ✅ User information
- ✅ Access control

Start managing your users with these powerful commands! 🚀
