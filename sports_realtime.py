"""
Real-time Sports Updates System
Delivers live scores, goals, and match updates within seconds
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

class SportsRealtimeUpdater:
    def __init__(self, bot_application):
        self.app = bot_application
        self.active_matches = {}  # Track live matches
        self.user_preferences = {}  # User league preferences
        self.last_updates = {}  # Track last update time per match
        
        # League IDs for different competitions
        self.leagues = {
            'premier_league': {'id': 39, 'name': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League', 'country': 'England'},
            'la_liga': {'id': 140, 'name': '🇪🇸 La Liga', 'country': 'Spain'},
            'bundesliga': {'id': 78, 'name': '🇩🇪 Bundesliga', 'country': 'Germany'},
            'serie_a': {'id': 135, 'name': '🇮🇹 Serie A', 'country': 'Italy'},
            'ligue_1': {'id': 61, 'name': '🇫🇷 Ligue 1', 'country': 'France'},
            'champions_league': {'id': 2, 'name': '🏆 Champions League', 'country': 'Europe'},
            'europa_league': {'id': 3, 'name': '🏆 Europa League', 'country': 'Europe'},
            'nba': {'id': 'nba', 'name': '🏀 NBA', 'country': 'USA'},
            'nfl': {'id': 'nfl', 'name': '🏈 NFL', 'country': 'USA'}
        }
        
        # API endpoints (you'll need to configure these)
        self.football_api = "https://api-football-v1.p.rapidapi.com/v3"
        self.api_key = None  # Set from environment
        
    async def start_realtime_updates(self):
        """Start background task for real-time updates"""
        while True:
            try:
                await self.check_live_matches()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logging.error(f"Realtime update error: {e}")
                await asyncio.sleep(30)
    
    async def check_live_matches(self):
        """Check for live matches and send updates"""
        try:
            # Get live matches from API
            live_matches = await self.fetch_live_matches()
            
            for match in live_matches:
                match_id = match['fixture']['id']
                
                # Check if this is a new event (goal, card, etc.)
                if self.has_new_event(match_id, match):
                    await self.send_match_update(match)
                    
        except Exception as e:
            logging.error(f"Error checking live matches: {e}")
    
    async def fetch_live_matches(self) -> List[Dict]:
        """Fetch live matches from API"""
        # This is a placeholder - implement with actual API
        # For now, return empty list
        return []
    
    def has_new_event(self, match_id: str, match: Dict) -> bool:
        """Check if match has new events since last update"""
        current_events = match.get('events', [])
        
        if match_id not in self.last_updates:
            self.last_updates[match_id] = {
                'events_count': len(current_events),
                'score': match['goals']
            }
            return True
        
        last = self.last_updates[match_id]
        
        # Check if score changed or new events
        if (len(current_events) > last['events_count'] or 
            match['goals'] != last['score']):
            self.last_updates[match_id] = {
                'events_count': len(current_events),
                'score': match['goals']
            }
            return True
        
        return False
    
    async def send_match_update(self, match: Dict):
        """Send real-time match update to subscribed users"""
        from database import SessionLocal, User
        
        league_id = match['league']['id']
        home_team = match['teams']['home']['name']
        away_team = match['teams']['away']['name']
        score = f"{match['goals']['home']} - {match['goals']['away']}"
        minute = match['fixture']['status']['elapsed']
        
        # Get latest event
        events = match.get('events', [])
        if events:
            latest_event = events[-1]
            event_type = latest_event['type']
            player = latest_event['player']['name']
            
            if event_type == 'Goal':
                message = (
                    f"⚽ GOAL! {minute}'\n\n"
                    f"{home_team} {score} {away_team}\n\n"
                    f"⚡ {player} scores!\n\n"
                    f"🏆 {match['league']['name']}"
                )
            elif event_type == 'Card':
                card = latest_event['detail']
                message = (
                    f"🟨 {card}! {minute}'\n\n"
                    f"{home_team} {score} {away_team}\n\n"
                    f"👤 {player}\n\n"
                    f"🏆 {match['league']['name']}"
                )
            else:
                return
            
            # Send to subscribed users
            db = SessionLocal()
            try:
                # Get users subscribed to this league
                users = db.query(User).filter(
                    User.is_premium == True,
                    User.sports_leagues.contains(str(league_id))
                ).all()
                
                for user in users:
                    try:
                        await self.app.bot.send_message(
                            chat_id=user.telegram_id,
                            text=message
                        )
                    except Exception as e:
                        logging.error(f"Failed to send update to {user.telegram_id}: {e}")
                        
            finally:
                db.close()
    
    def set_user_leagues(self, user_id: int, leagues: List[str]):
        """Set user's preferred leagues"""
        self.user_preferences[user_id] = leagues
    
    def get_user_leagues(self, user_id: int) -> List[str]:
        """Get user's preferred leagues"""
        return self.user_preferences.get(user_id, ['premier_league'])
    
    async def get_live_scores(self, league: str = None) -> List[Dict]:
        """Get current live scores"""
        # Placeholder for live scores API call
        return []
    
    async def get_upcoming_matches(self, league: str, hours: int = 24) -> List[Dict]:
        """Get upcoming matches in next X hours"""
        # Placeholder for upcoming matches API call
        return []


# Global instance
sports_updater = None

def init_sports_updater(bot_application):
    """Initialize sports updater"""
    global sports_updater
    sports_updater = SportsRealtimeUpdater(bot_application)
    return sports_updater

def get_sports_updater():
    """Get sports updater instance"""
    return sports_updater
