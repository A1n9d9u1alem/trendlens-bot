"""
Video Handler for TrendLens Bot
Handles video preview/playback for YouTube, TikTok, Reddit, and other platforms
"""

import re
import requests
from typing import Optional, Dict, Tuple


class VideoHandler:
    """Extract and handle video URLs for in-app playback"""
    
    def __init__(self):
        self.youtube_regex = r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})'
        self.tiktok_regex = r'(?:tiktok\.com/@[\w.-]+/video/|vm\.tiktok\.com/)(\d+)'
        self.reddit_video_regex = r'v\.redd\.it/([a-zA-Z0-9]+)'
        self.twitter_regex = r'(?:twitter\.com|x\.com)/\w+/status/(\d+)'
        
    def is_video_url(self, url: str) -> bool:
        """Check if URL is a video"""
        if not url:
            return False
            
        url_lower = url.lower()
        
        # YouTube
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return True
        
        # TikTok
        if 'tiktok.com' in url_lower:
            return True
        
        # Reddit video
        if 'v.redd.it' in url_lower:
            return True
        
        # Twitter/X video
        if ('twitter.com' in url_lower or 'x.com' in url_lower) and '/status/' in url_lower:
            return True
        
        # Direct video files
        if any(url_lower.endswith(ext) for ext in ['.mp4', '.webm', '.mov', '.avi', '.mkv']):
            return True
        
        return False
    
    def extract_video_id(self, url: str, platform: str) -> Optional[str]:
        """Extract video ID from URL"""
        if platform == 'youtube':
            match = re.search(self.youtube_regex, url)
            return match.group(1) if match else None
        
        elif platform == 'tiktok':
            match = re.search(self.tiktok_regex, url)
            return match.group(1) if match else None
        
        elif platform == 'reddit':
            match = re.search(self.reddit_video_regex, url)
            return match.group(1) if match else None
        
        elif platform == 'twitter':
            match = re.search(self.twitter_regex, url)
            return match.group(1) if match else None
        
        return None
    
    def get_youtube_embed_url(self, video_id: str) -> str:
        """Get YouTube embed URL"""
        return f"https://www.youtube.com/embed/{video_id}"
    
    def get_youtube_thumbnail(self, video_id: str, quality: str = 'maxresdefault') -> str:
        """Get YouTube thumbnail URL
        
        Quality options: maxresdefault, hqdefault, mqdefault, sddefault, default
        """
        return f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
    
    def get_video_info(self, url: str, platform: str) -> Dict[str, str]:
        """Get video information for embedding"""
        video_info = {
            'url': url,
            'platform': platform,
            'is_video': False,
            'embed_url': None,
            'thumbnail': None,
            'video_id': None
        }
        
        if platform == 'youtube':
            video_id = self.extract_video_id(url, 'youtube')
            if video_id:
                video_info['is_video'] = True
                video_info['video_id'] = video_id
                video_info['embed_url'] = self.get_youtube_embed_url(video_id)
                video_info['thumbnail'] = self.get_youtube_thumbnail(video_id)
        
        elif platform == 'tiktok':
            video_id = self.extract_video_id(url, 'tiktok')
            if video_id:
                video_info['is_video'] = True
                video_info['video_id'] = video_id
        
        elif platform == 'reddit':
            if 'v.redd.it' in url:
                video_info['is_video'] = True
        
        elif platform == 'twitter':
            video_id = self.extract_video_id(url, 'twitter')
            if video_id:
                video_info['is_video'] = True
                video_info['video_id'] = video_id
        
        return video_info
    
    def get_direct_video_url(self, url: str, platform: str) -> Optional[str]:
        """Try to get direct video URL for platforms that support it"""
        
        # For Reddit videos, try to get direct MP4 URL
        if platform == 'reddit' and 'v.redd.it' in url:
            try:
                # Reddit video URLs typically end with /DASH_xxx.mp4
                # Try common resolutions
                for quality in ['720', '480', '360', '240']:
                    video_url = f"{url}/DASH_{quality}.mp4"
                    response = requests.head(video_url, timeout=3, allow_redirects=True)
                    if response.status_code == 200:
                        return video_url
            except:
                pass
        
        # For direct video files
        if any(url.lower().endswith(ext) for ext in ['.mp4', '.webm', '.mov']):
            return url
        
        return None
    
    def format_video_caption(self, title: str, platform: str, description: str = "", 
                            index: int = 0, total: int = 0, is_premium: bool = False) -> str:
        """Format caption for video message"""
        caption = f"🎬 {title}\n\n"
        caption += f"📱 Platform: {platform.upper()}\n"
        
        if is_premium and description:
            caption += f"📝 {description[:100]}...\n\n"
        
        if total > 0:
            caption += f"📊 Item {index+1}/{total}"
        
        return caption[:1024]  # Telegram caption limit
    
    def should_send_as_video(self, url: str, platform: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if content should be sent as video and return video URL
        
        Returns:
            (should_send_as_video: bool, video_url: Optional[str])
        """
        if not self.is_video_url(url):
            return False, None
        
        # Try to get direct video URL
        direct_url = self.get_direct_video_url(url, platform)
        if direct_url:
            return True, direct_url
        
        # For YouTube, we can't send direct video but can send thumbnail + link
        if platform == 'youtube':
            video_id = self.extract_video_id(url, 'youtube')
            if video_id:
                # Return thumbnail URL for photo message
                return False, self.get_youtube_thumbnail(video_id)
        
        return False, None
