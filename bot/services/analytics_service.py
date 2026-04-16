"""
Analytics Service Module
Handles analytics tracking and reporting
"""

from database import Analytics
import json


class AnalyticsService:
    """Analytics service for tracking user events"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    def track_event(self, db, user_id, event_type, category=None, metadata=None):
        """Track user analytics event"""
        try:
            analytics = Analytics(
                user_id=user_id,
                event_type=event_type,
                category=category,
                event_data=json.dumps(metadata) if metadata else None
            )
            db.add(analytics)
            db.commit()
        except:
            pass
