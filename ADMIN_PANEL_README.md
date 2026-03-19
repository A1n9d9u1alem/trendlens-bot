# TrendLens Admin Panel

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Admin Credentials
Edit `.env` file:
```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
ADMIN_SECRET_KEY=your_random_secret_key
```

### 3. Run Admin Panel
```bash
python admin_panel.py
```

### 4. Access Dashboard
Open browser: `http://localhost:5000`

Default credentials:
- Username: `admin`
- Password: `admin123`

**⚠️ IMPORTANT: Change default password in production!**

---

## 📊 Features

### Dashboard Overview
- **Total Users** - All registered users
- **Pro Users** - Active premium subscribers
- **Active Users (7d)** - Users active in last 7 days
- **New Today** - New registrations today
- **Pending Payments** - Awaiting approval
- **Revenue** - Total earnings from Pro subscriptions

### User Management
- View all users with filters (All/Pro/Free)
- See subscription status and expiry dates
- Revoke Pro access from users
- Real-time user statistics

### Payment Management
- View pending payment confirmations
- Approve payments (grants 30 days Pro access)
- Reject invalid payments
- Track payment references

### Analytics
- Category view statistics
- User engagement metrics
- Content performance tracking

---

## 🔒 Security

- Session-based authentication
- Login required for all admin routes
- Secure password handling
- CSRF protection via Flask sessions

---

## 🌐 Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 admin_panel:app
```

### Using Railway/Render
Add to `Procfile`:
```
web: gunicorn admin_panel:app
```

### Environment Variables
Set these in production:
- `ADMIN_USERNAME` - Your admin username
- `ADMIN_PASSWORD` - Strong password
- `ADMIN_SECRET_KEY` - Random secret key (use `python -c "import secrets; print(secrets.token_hex(32))"`)
- `DATABASE_URL` - PostgreSQL connection string

---

## 📱 Mobile Responsive

The admin panel is fully responsive and works on:
- Desktop browsers
- Tablets
- Mobile phones

---

## 🔄 Auto-Refresh

Dashboard statistics auto-refresh every 30 seconds to show real-time data.

---

## 🎨 Modern UI Features

- Gradient design with purple theme
- Clean card-based layout
- Smooth transitions and hover effects
- Intuitive tab navigation
- Color-coded badges (Pro/Free/Pending)
- Responsive tables

---

## 📞 Support

For issues or questions, contact the bot admin.
