"""
Real-time Dashboard with WebSocket Support
Provides live updates for admin panel
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
from functools import wraps
import os
from datetime import datetime, timedelta, timezone
from database import SessionLocal, User, Content, Payment, Analytics
from sqlalchemy import func, desc
from dotenv import load_dotenv
import threading
import time

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('ADMIN_SECRET_KEY', 'your-secret-key-change-this')
socketio = SocketIO(app, cors_allowed_origins="*")

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# Store connected clients
connected_clients = set()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_live_stats():
    """Get current statistics"""
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        pro_users = db.query(User).filter(User.is_premium == True).count()
        pending_payments = db.query(Payment).filter(Payment.status == 'submitted').count()
        
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        active_users = db.query(Analytics).filter(Analytics.timestamp >= week_ago).distinct(Analytics.user_id).count()
        
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        new_today = db.query(User).filter(User.created_at >= today).count()
        
        total_content = db.query(Content).count()
        
        # Get recent activity (last 5 minutes)
        five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_activity = db.query(Analytics).filter(Analytics.timestamp >= five_min_ago).count()
        
        return {
            'total_users': total_users,
            'pro_users': pro_users,
            'free_users': total_users - pro_users,
            'active_users': active_users,
            'new_today': new_today,
            'pending_payments': pending_payments,
            'total_content': total_content,
            'revenue': pro_users * 5,
            'recent_activity': recent_activity,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    finally:
        db.close()

def broadcast_stats():
    """Broadcast stats to all connected clients"""
    while True:
        try:
            if connected_clients:
                stats = get_live_stats()
                socketio.emit('stats_update', stats, namespace='/')
            time.sleep(5)  # Update every 5 seconds
        except Exception as e:
            print(f"Broadcast error: {e}")
            time.sleep(5)

# Start background thread for broadcasting
stats_thread = threading.Thread(target=broadcast_stats, daemon=True)
stats_thread.start()

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    connected_clients.add(request.sid)
    print(f"Client connected: {request.sid}")
    # Send initial stats
    stats = get_live_stats()
    emit('stats_update', stats)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    connected_clients.discard(request.sid)
    print(f"Client disconnected: {request.sid}")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        if data.get('username') == ADMIN_USERNAME and data.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Invalid credentials'})
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard_realtime.html')

@app.route('/api/stats')
@login_required
def get_stats():
    return jsonify(get_live_stats())

@app.route('/api/users')
@login_required
def get_users():
    db = SessionLocal()
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        filter_type = request.args.get('filter', 'all')
        
        query = db.query(User)
        if filter_type == 'pro':
            query = query.filter(User.is_premium == True)
        elif filter_type == 'free':
            query = query.filter(User.is_premium == False)
        
        total = query.count()
        users = query.order_by(desc(User.created_at)).offset((page-1)*per_page).limit(per_page).all()
        
        return jsonify({
            'users': [{
                'id': u.id,
                'telegram_id': u.telegram_id,
                'username': u.username,
                'is_premium': u.is_premium,
                'subscription_end': u.subscription_end.isoformat() if u.subscription_end else None,
                'created_at': u.created_at.isoformat() if u.created_at else None
            } for u in users],
            'total': total,
            'page': page,
            'pages': (total + per_page - 1) // per_page
        })
    finally:
        db.close()

@app.route('/api/payments')
@login_required
def get_payments():
    db = SessionLocal()
    try:
        status = request.args.get('status', 'submitted')
        payments = db.query(Payment).filter(Payment.status == status).order_by(desc(Payment.created_at)).limit(50).all()
        
        result = []
        for p in payments:
            user = db.query(User).filter(User.id == p.user_id).first()
            result.append({
                'id': p.id,
                'user_id': user.telegram_id if user else None,
                'username': user.username if user else 'Unknown',
                'amount': p.amount,
                'reference': p.reference,
                'status': p.status,
                'created_at': p.created_at.isoformat() if p.created_at else None
            })
        
        return jsonify({'payments': result})
    finally:
        db.close()

@app.route('/api/payment/approve', methods=['POST'])
@login_required
def approve_payment():
    db = SessionLocal()
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        days = data.get('days', 30)
        
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        user.is_premium = True
        sub_end = user.subscription_end
        if sub_end and sub_end.tzinfo is None:
            sub_end = sub_end.replace(tzinfo=timezone.utc)
        
        if sub_end and sub_end > datetime.now(timezone.utc):
            user.subscription_end = sub_end + timedelta(days=days)
        else:
            user.subscription_end = datetime.now(timezone.utc) + timedelta(days=days)
        
        payment = db.query(Payment).filter(Payment.user_id == user.id, Payment.status == 'submitted').first()
        if payment:
            payment.status = 'approved'
            payment.approved_at = datetime.now(timezone.utc)
        
        db.commit()
        
        # Broadcast update
        socketio.emit('payment_approved', {
            'user_id': telegram_id,
            'username': user.username
        })
        
        return jsonify({'success': True})
    finally:
        db.close()

@app.route('/api/payment/reject', methods=['POST'])
@login_required
def reject_payment():
    db = SessionLocal()
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        payment = db.query(Payment).filter(Payment.user_id == user.id, Payment.status == 'submitted').first()
        if payment:
            payment.status = 'rejected'
            db.commit()
        
        return jsonify({'success': True})
    finally:
        db.close()

@app.route('/api/user/revoke', methods=['POST'])
@login_required
def revoke_user():
    db = SessionLocal()
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        user.is_premium = False
        user.subscription_end = None
        db.commit()
        
        return jsonify({'success': True})
    finally:
        db.close()

@app.route('/api/user/grant', methods=['POST'])
@login_required
def grant_pro():
    db = SessionLocal()
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        days = data.get('days', 30)
        
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        user.is_premium = True
        sub_end = user.subscription_end
        if sub_end and sub_end.tzinfo is None:
            sub_end = sub_end.replace(tzinfo=timezone.utc)
        
        if sub_end and sub_end > datetime.now(timezone.utc):
            user.subscription_end = sub_end + timedelta(days=days)
        else:
            user.subscription_end = datetime.now(timezone.utc) + timedelta(days=days)
        
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()

@app.route('/api/user/ban', methods=['POST'])
@login_required
def ban_user():
    db = SessionLocal()
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        from sqlalchemy import text
        db.execute(
            text("UPDATE users SET is_banned = TRUE WHERE telegram_id = :tid"),
            {"tid": telegram_id}
        )
        db.commit()
        return jsonify({'success': True, 'message': f'User {telegram_id} banned successfully'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    finally:
        db.close()

@app.route('/api/user/unban', methods=['POST'])
@login_required
def unban_user():
    db = SessionLocal()
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        from sqlalchemy import text
        db.execute(
            text("UPDATE users SET is_banned = FALSE WHERE telegram_id = :tid"),
            {"tid": telegram_id}
        )
        db.commit()
        return jsonify({'success': True, 'message': f'User {telegram_id} unbanned successfully'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    finally:
        db.close()

@app.route('/api/analytics')
@login_required
def get_analytics():
    db = SessionLocal()
    try:
        days = int(request.args.get('days', 7))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        category_stats = db.query(
            Analytics.category, 
            func.count(Analytics.id).label('count')
        ).filter(
            Analytics.timestamp >= cutoff,
            Analytics.category.isnot(None)
        ).group_by(Analytics.category).all()
        
        return jsonify({
            'categories': [{'name': c[0], 'count': c[1]} for c in category_stats]
        })
    finally:
        db.close()

@app.route('/api/content/list')
@login_required
def list_content():
    db = SessionLocal()
    try:
        category = request.args.get('category', 'all')
        page = int(request.args.get('page', 1))
        per_page = 20
        
        query = db.query(Content)
        if category != 'all':
            query = query.filter(Content.category == category)
        
        total = query.count()
        contents = query.order_by(desc(Content.created_at)).offset((page-1)*per_page).limit(per_page).all()
        
        return jsonify({
            'contents': [{
                'id': c.id,
                'title': c.title,
                'platform': c.platform,
                'category': c.category,
                'url': c.url,
                'engagement_score': c.engagement_score,
                'created_at': c.created_at.isoformat() if c.created_at else None
            } for c in contents],
            'total': total,
            'page': page,
            'pages': (total + per_page - 1) // per_page
        })
    finally:
        db.close()

@app.route('/api/content/delete', methods=['POST'])
@login_required
def delete_content():
    db = SessionLocal()
    try:
        data = request.get_json()
        content_id = data.get('content_id')
        
        content = db.query(Content).filter(Content.id == content_id).first()
        if content:
            db.delete(content)
            db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Content not found'})
    finally:
        db.close()

@app.route('/api/broadcast', methods=['POST'])
@login_required
def broadcast():
    db = SessionLocal()
    try:
        data = request.get_json()
        message = data.get('message', '')
        target = data.get('target', 'all')
        
        query = db.query(User)
        if target == 'pro':
            query = query.filter(User.is_premium == True)
        elif target == 'free':
            query = query.filter(User.is_premium == False)
        
        users = query.all()
        return jsonify({
            'success': True,
            'message': f'Broadcast queued for {len(users)} users',
            'count': len(users)
        })
    finally:
        db.close()

@app.route('/api/system/stats')
@login_required
def system_stats():
    db = SessionLocal()
    try:
        total_content = db.query(Content).count()
        
        return jsonify({
            'total_content': total_content,
            'database': 'Connected'
        })
    finally:
        db.close()

@app.route('/api/system/clear-cache', methods=['POST'])
@login_required
def clear_cache():
    try:
        import redis
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            r = redis.from_url(redis_url, decode_responses=False)
            r.flushdb()
            r.close()
            return jsonify({'success': True, 'message': 'Redis cache cleared successfully'})
        return jsonify({'success': False, 'message': 'Redis not configured'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/system/clear-old-content', methods=['POST'])
@login_required
def clear_old_content():
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        deleted = db.query(Content).filter(Content.created_at < cutoff).delete()
        db.commit()
        
        return jsonify({'success': True, 'message': f'Deleted {deleted} old content items'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    finally:
        db.close()

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🔥 TrendLens Real-Time Dashboard")
    print("="*50)
    print(f"\n✅ Dashboard running at: http://localhost:5000")
    print(f"✅ Alternative URL: http://127.0.0.1:5000")
    print(f"\n👤 Login with:")
    print(f"   Username: {ADMIN_USERNAME}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print("\n" + "="*50 + "\n")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
