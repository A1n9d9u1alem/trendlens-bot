"""
Thumbnail Handler for TrendLens Bot
Fixes missing and broken thumbnails with smart fallbacks
"""

import requests
import re
from typing import Optional, Dict, List
import logging


class ThumbnailHandler:
    """Handle thumbnail extraction, validation, and fallbacks"""
    
    def __init__(self):
        self.timeout = 5  # seconds
        self.max_retries = 2
        self.cache = {}  # Simple in-memory cache
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; TrendLensBot/1.0)'})
        
    def validate_thumbnail(self, url: str) -> bool:
        """
        Validate if thumbnail URL is accessible
        
        Args:
            url: Thumbnail URL to validate
            
        Returns:
            True if thumbnail is valid and accessible
        """
        if not url or not url.startswith('http'):
            return False
        
        # Check cache first
        if url in self.cache:
            return self.cache[url]
        
        try:
            # Try HEAD first, fallback to GET
            try:
                response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            except:
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True, stream=True)
            
            # Accept 200 or 304 (cached)
            if response.status_code not in [200, 304]:
                self.cache[url] = False
                return False
            
            # Check content type if available
            content_type = response.headers.get('content-type', '').lower()
            if content_type and not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'gif', 'webp', 'octet-stream']):
                self.cache[url] = False
                return False
            
            self.cache[url] = True
            return True
            
        except Exception as e:
            logging.debug(f"Thumbnail validation failed for {url}: {e}")
            # Don't cache failures - might be temporary
            return False
    
    def get_reddit_thumbnail(self, url: str, post_data: Dict = None) -> Optional[str]:
        """
        Get Reddit thumbnail with multiple fallback strategies
        
        Priority:
        1. Preview image (highest quality)
        2. Thumbnail from post data
        3. Extract from URL patterns
        4. Default Reddit thumbnail
        """
        thumbnails = []
        
        # Strategy 1: Preview image from post data
        if post_data:
            preview = post_data.get('preview')
            if preview and isinstance(preview, dict):
                images = preview.get('images', [])
                if images and len(images) > 0:
                    # Get source image first (highest quality)
                    source = images[0].get('source', {})
                    source_url = source.get('url', '').replace('&amp;', '&')
                    if source_url:
                        thumbnails.append(source_url)
                    
                    # Get highest resolution
                    resolutions = images[0].get('resolutions', [])
                    if resolutions:
                        highest_res = resolutions[-1]
                        thumb_url = highest_res.get('url', '').replace('&amp;', '&')
                        if thumb_url:
                            thumbnails.append(thumb_url)
        
        # Strategy 2: Direct thumbnail from post data
        if post_data:
            thumb = post_data.get('thumbnail')
            if thumb and thumb.startswith('http') and 'self' not in thumb and 'default' not in thumb:
                thumbnails.append(thumb)
        
        # Strategy 3: Extract from URL patterns
        if 'i.redd.it' in url:
            thumbnails.append(url)
        elif 'preview.redd.it' in url:
            thumbnails.append(url)
        elif '/r/' in url and 'reddit.com' in url:
            # Try to construct preview URL
            post_id = self._extract_reddit_post_id(url)
            if post_id:
                preview_url = f"https://preview.redd.it/{post_id}.jpg"
                thumbnails.append(preview_url)
        
        # Strategy 4: Default Reddit thumbnail
        thumbnails.append("https://www.redditstatic.com/desktop2x/img/favicon/android-icon-192x192.png")
        
        # Return first working thumbnail (validate only first 3 to save time)
        for i, thumb in enumerate(thumbnails):
            if i < 3 and self.validate_thumbnail(thumb):
                return thumb
            elif i >= 3:
                return thumb  # Return fallback without validation
        
        return thumbnails[-1] if thumbnails else None
    
    def get_youtube_thumbnail(self, video_id: str, quality: str = 'maxresdefault') -> Optional[str]:
        """
        Get YouTube thumbnail with quality fallbacks
        
        Quality options (in order of preference):
        1. maxresdefault (1280x720)
        2. sddefault (640x480)
        3. hqdefault (480x360)
        4. mqdefault (320x180)
        5. default (120x90)
        """
        if not video_id:
            return None
        
        # YouTube thumbnails are always available, return without validation
        return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    
    def get_twitter_thumbnail(self, url: str, tweet_data: Dict = None) -> Optional[str]:
        """Get Twitter thumbnail with fallbacks"""
        thumbnails = []
        
        # Strategy 1: From tweet data
        if tweet_data:
            media = tweet_data.get('media', [])
            if media and len(media) > 0:
                media_url = media[0].get('media_url_https') or media[0].get('media_url')
                if media_url:
                    thumbnails.append(media_url)
        
        # Strategy 2: Default Twitter icon
        thumbnails.append("https://abs.twimg.com/icons/apple-touch-icon-192x192.png")
        
        for thumb in thumbnails:
            if self.validate_thumbnail(thumb):
                return thumb
        
        return None
    
    def get_imgur_thumbnail(self, image_id: str) -> Optional[str]:
        """Get Imgur thumbnail with fallbacks"""
        if not image_id:
            return None
        
        # Remove extension if present
        image_id = image_id.split('.')[0]
        
        # Try different formats
        formats = ['jpg', 'png', 'gif']
        sizes = ['', 'l', 'm', 's']  # Full, large, medium, small
        
        for size in sizes:
            for fmt in formats:
                thumb_url = f"https://i.imgur.com/{image_id}{size}.{fmt}"
                if self.validate_thumbnail(thumb_url):
                    return thumb_url
        
        return None
    
    def get_generic_thumbnail(self, url: str, platform: str) -> Optional[str]:
        """Get generic platform thumbnail as fallback"""
        platform_icons = {
            'reddit': 'https://www.redditstatic.com/desktop2x/img/favicon/android-icon-192x192.png',
            'youtube': 'https://i.imgur.com/qoH1J1L.png',
            'twitter': 'https://abs.twimg.com/icons/apple-touch-icon-192x192.png',
            'tiktok': 'https://i.imgur.com/8XK3VJy.png',
            'imgur': 'https://s.imgur.com/images/favicon-152.png',
            'instagram': 'https://i.imgur.com/OAVVCjN.png',
            'news': 'https://i.imgur.com/9Y5p3QJ.png',
            'upwork': 'https://i.imgur.com/kMYxfGq.png',
            'fiverr': 'https://i.imgur.com/7wDqPJm.png'
        }
        
        return platform_icons.get(platform.lower(), 'https://i.imgur.com/qoH1J1L.png')
    
    def extract_thumbnail_from_html(self, url: str) -> Optional[str]:
        """Extract thumbnail from HTML meta tags (Open Graph, Twitter Card)"""
        try:
            response = requests.get(url, timeout=self.timeout, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; TrendLensBot/1.0)'
            })
            
            if response.status_code != 200:
                return None
            
            html = response.text
            
            # Try Open Graph image
            og_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if og_match:
                thumb_url = og_match.group(1)
                if self.validate_thumbnail(thumb_url):
                    return thumb_url
            
            # Try Twitter Card image
            twitter_match = re.search(r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if twitter_match:
                thumb_url = twitter_match.group(1)
                if self.validate_thumbnail(thumb_url):
                    return thumb_url
            
            # Try standard meta image
            meta_match = re.search(r'<meta\s+name=["\']image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if meta_match:
                thumb_url = meta_match.group(1)
                if self.validate_thumbnail(thumb_url):
                    return thumb_url
            
        except Exception as e:
            logging.debug(f"HTML thumbnail extraction failed for {url}: {e}")
        
        return None
    
    def get_thumbnail(self, url: str, platform: str, content_data: Dict = None) -> Optional[str]:
        """
        Main method to get thumbnail with comprehensive fallback strategy
        
        Args:
            url: Content URL
            platform: Platform name (reddit, youtube, twitter, etc.)
            content_data: Additional content metadata
            
        Returns:
            Valid thumbnail URL or None
        """
        platform = platform.lower()
        
        # Try existing thumbnail from content_data first (fastest)
        if content_data:
            existing_thumb = content_data.get('thumbnail')
            if existing_thumb and existing_thumb.startswith('http'):
                # Quick validation for known good domains
                if any(domain in existing_thumb for domain in ['imgur.com', 'youtube.com', 'redd.it', 'ytimg.com']):
                    return self.fix_thumbnail_url(existing_thumb)
        
        # Try platform-specific extraction
        if platform == 'reddit':
            thumb = self.get_reddit_thumbnail(url, content_data)
            if thumb:
                return thumb
        
        elif platform == 'youtube':
            video_id = self._extract_youtube_id(url)
            if video_id:
                thumb = self.get_youtube_thumbnail(video_id)
                if thumb:
                    return thumb
        
        elif platform == 'twitter' or platform == 'x':
            thumb = self.get_twitter_thumbnail(url, content_data)
            if thumb:
                return thumb
        
        elif platform == 'imgur':
            image_id = self._extract_imgur_id(url)
            if image_id:
                thumb = self.get_imgur_thumbnail(image_id)
                if thumb:
                    return thumb
        
        # Try existing thumbnail from content_data (with validation)
        if content_data:
            existing_thumb = content_data.get('thumbnail')
            if existing_thumb and existing_thumb.startswith('http'):
                return self.fix_thumbnail_url(existing_thumb)
        
        # Fallback to generic platform icon (always works)
        return self.get_generic_thumbnail(url, platform)
    
    def fix_thumbnail_url(self, url: str) -> str:
        """Fix common thumbnail URL issues"""
        if not url:
            return url
        
        # Fix HTML entities
        url = url.replace('&amp;', '&')
        
        # Fix protocol
        if url.startswith('//'):
            url = 'https:' + url
        
        # Remove query parameters that might break loading
        if '?' in url and any(domain in url for domain in ['redd.it', 'imgur.com']):
            url = url.split('?')[0]
        
        return url
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_imgur_id(self, url: str) -> Optional[str]:
        """Extract Imgur image ID from URL"""
        match = re.search(r'imgur\.com/(?:a/|gallery/)?([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        return None
    
    def _extract_reddit_post_id(self, url: str) -> Optional[str]:
        """Extract Reddit post ID from URL"""
        match = re.search(r'/comments/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        return None
    
    def get_thumbnail_info(self, url: str, platform: str, content_data: Dict = None) -> Dict:
        """
        Get comprehensive thumbnail information
        
        Returns:
            {
                'thumbnail': str,
                'is_valid': bool,
                'source': str,  # 'platform', 'html', 'generic'
                'quality': str  # 'high', 'medium', 'low'
            }
        """
        info = {
            'thumbnail': None,
            'is_valid': False,
            'source': 'none',
            'quality': 'none'
        }
        
        # Get thumbnail
        thumb = self.get_thumbnail(url, platform, content_data)
        
        if thumb:
            info['thumbnail'] = thumb
            info['is_valid'] = True
            
            # Determine source
            if platform in thumb.lower():
                info['source'] = 'platform'
            elif any(domain in thumb for domain in ['flaticon', 'favicon', 'icon']):
                info['source'] = 'generic'
            else:
                info['source'] = 'html'
            
            # Determine quality
            if 'maxres' in thumb or '1280' in thumb or '720' in thumb:
                info['quality'] = 'high'
            elif any(q in thumb for q in ['hq', 'sd', '480', '640']):
                info['quality'] = 'medium'
            else:
                info['quality'] = 'low'
        
        return info
    
    def clear_cache(self):
        """Clear thumbnail validation cache"""
        self.cache.clear()
