#!/usr/bin/env python3
"""
Health Check Server for TrendLens Bot
Runs on port 8080 for monitoring
"""

from flask import Flask, jsonify
from database import SessionLocal, User, Content
from datetime import datetime, timezone
import redis
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/health')
def health():
    """Basic health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'service': 'trendlens-bot'
    }), 200

@app.route('/health/detailed')
def health_detailed():
    """Detailed health check with dependencies"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'checks': {}
    }
    
    # Check database
    try:
        db = SessionLocal()
        user_count = db.query(User).count()
        db.close()
        health_status['checks']['database'] = {
            'status': 'up',
            'users': user_count
        }
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['checks']['database'] = {
            'status': 'down',
            'error': str(e)
        }
    
    # Check Redis
    try:
        r = redis.Redis.from_url(os.getenv('REDIS_URL'), ssl=True, ssl_cert_reqs=None)
        r.ping()
        health_status['checks']['redis'] = {'status': 'up'}
    except Exception as e:
        health_status['status'] = 'degraded'
        health_status['checks']['redis'] = {
            'status': 'down',
            'error': str(e)
        }
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code

@app.route('/metrics')
def metrics():
    """Prometheus-style metrics"""
    try:
        db = SessionLocal()
        total_users = db.query(User).count()
        pro_users = db.query(User).filter(User.is_premium == True).count()
        total_content = db.query(Content).count()
        db.close()
        
        metrics_text = f"""# HELP trendlens_users_total Total number of users
# TYPE trendlens_users_total gauge
trendlens_users_total {total_users}

# HELP trendlens_users_pro Number of pro users
# TYPE trendlens_users_pro gauge
trendlens_users_pro {pro_users}

# HELP trendlens_content_total Total content items
# TYPE trendlens_content_total gauge
trendlens_content_total {total_content}
"""
        return metrics_text, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return f"# Error: {e}", 500, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    port = int(os.getenv('HEALTH_PORT', 8080))
    app.run(host='0.0.0.0', port=port)
