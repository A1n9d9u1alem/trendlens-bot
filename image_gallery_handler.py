"""
Image Gallery Handler for TrendLens Bot
Handles multi-image posts from Reddit, Twitter, and other platforms
"""

import re
import requests
from typing import List, Dict, Optional, Tuple
import logging


class ImageGalleryHandler:
    """Handle multi-image posts and galleries"""
    
    def __init__(self):
        self.max_images_per_gallery = 10  # Telegram limit
        self.reddit_gallery_regex = r'reddit\.com/gallery/([a-zA-Z0-9]+)'
        self.imgur_album_regex = r'imgur\.com/(?:a|gallery)/([a-zA-Z0-9]+)'
        
    def is_gallery_url(self, url: str) -> bool:
        """Check if URL is a gallery/multi-image post"""
        if not url:
            return False
            
        url_lower = url.lower()
        
        # Reddit gallery
        if '/gallery/' in url_lower and 'reddit.com' in url_lower:
            return True
        
        # Imgur album
        if ('imgur.com/a/' in url_lower or 'imgur.com/gallery/' in url_lower):
            return True
        
        # Twitter thread with images (detected by platform)
        if ('twitter.com' in url_lower or 'x.com' in url_lower) and '/status/' in url_lower:
            return True  # May have multiple images
        
        return False
    
    def extract_gallery_id(self, url: str, platform: str) -> Optional[str]:
        """Extract gallery ID from URL"""
        if platform == 'reddit':
            match = re.search(self.reddit_gallery_regex, url)
            return match.group(1) if match else None
        
        elif platform == 'imgur':
            match = re.search(self.imgur_album_regex, url)
            return match.group(1) if match else None
        
        return None
    
    def parse_reddit_gallery(self, content_dict: Dict) -> List[str]:
        """
        Parse Reddit gallery data from content dictionary
        
        Expected format in content_dict:
        {
            'url': 'https://reddit.com/gallery/abc123',
            'description': 'JSON with media_metadata',
            'thumbnail': 'first_image_url'
        }
        """
        images = []
        
        try:
            # Try to get images from description (if aggregator stored them)
            description = content_dict.get('description', '')
            
            # Check if thumbnail exists (first image)
            thumbnail = content_dict.get('thumbnail')
            if thumbnail and thumbnail.startswith('http'):
                images.append(thumbnail)
            
            # Parse additional images from description if available
            # Format: "Image 1: url1 | Image 2: url2"
            if '|' in description:
                parts = description.split('|')
                for part in parts:
                    if 'http' in part:
                        # Extract URL from text
                        urls = re.findall(r'https?://[^\s]+', part)
                        for url in urls:
                            if url not in images and len(images) < self.max_images_per_gallery:
                                images.append(url.strip())
            
            # If no images found, try to extract from URL patterns in description
            if not images:
                urls = re.findall(r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp)', description)
                images.extend(urls[:self.max_images_per_gallery])
            
        except Exception as e:
            logging.error(f"Error parsing Reddit gallery: {e}")
        
        return images[:self.max_images_per_gallery]
    
    def parse_imgur_album(self, album_id: str) -> List[str]:
        """
        Parse Imgur album to get image URLs
        Note: Requires Imgur API for full functionality
        """
        images = []
        
        try:
            # Try direct image URLs (common pattern)
            # Imgur albums often have sequential IDs
            base_url = f"https://i.imgur.com/{album_id}"
            
            # Try common extensions
            for ext in ['jpg', 'png', 'gif']:
                img_url = f"{base_url}.{ext}"
                try:
                    response = requests.head(img_url, timeout=2)
                    if response.status_code == 200:
                        images.append(img_url)
                        break
                except:
                    continue
            
        except Exception as e:
            logging.error(f"Error parsing Imgur album: {e}")
        
        return images
    
    def get_gallery_images(self, url: str, platform: str, content_dict: Dict = None) -> List[str]:
        """
        Get all images from a gallery URL
        
        Args:
            url: Gallery URL
            platform: Platform name (reddit, imgur, twitter)
            content_dict: Content dictionary with metadata
            
        Returns:
            List of image URLs
        """
        images = []
        
        try:
            if platform == 'reddit' and content_dict:
                images = self.parse_reddit_gallery(content_dict)
            
            elif platform == 'imgur':
                gallery_id = self.extract_gallery_id(url, 'imgur')
                if gallery_id:
                    images = self.parse_imgur_album(gallery_id)
            
            # Fallback: try to get thumbnail at least
            if not images and content_dict:
                thumbnail = content_dict.get('thumbnail')
                if thumbnail and thumbnail.startswith('http'):
                    images.append(thumbnail)
        
        except Exception as e:
            logging.error(f"Error getting gallery images: {e}")
        
        return images[:self.max_images_per_gallery]
    
    def validate_image_url(self, url: str) -> bool:
        """Validate if URL is a valid image"""
        if not url or not url.startswith('http'):
            return False
        
        # Check if URL ends with image extension
        url_lower = url.lower()
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        
        # Check extension
        if any(url_lower.endswith(ext) for ext in valid_extensions):
            return True
        
        # Check if URL contains image indicators
        if any(indicator in url_lower for indicator in ['i.redd.it', 'i.imgur.com', 'preview.redd.it']):
            return True
        
        return False
    
    def clean_image_urls(self, urls: List[str]) -> List[str]:
        """Clean and validate image URLs"""
        cleaned = []
        
        for url in urls:
            # Remove query parameters that might break image loading
            clean_url = url.split('?')[0] if '?' in url else url
            
            # Validate
            if self.validate_image_url(clean_url):
                cleaned.append(clean_url)
        
        return cleaned
    
    def should_send_as_gallery(self, url: str, platform: str, content_dict: Dict = None) -> Tuple[bool, List[str]]:
        """
        Determine if content should be sent as gallery
        
        Returns:
            (should_send_as_gallery: bool, image_urls: List[str])
        """
        # Check if it's a gallery URL
        if not self.is_gallery_url(url):
            return False, []
        
        # Try to get images
        images = self.get_gallery_images(url, platform, content_dict)
        
        # Clean and validate
        images = self.clean_image_urls(images)
        
        # Need at least 2 images for a gallery
        if len(images) >= 2:
            return True, images
        
        # Single image - not a gallery
        if len(images) == 1:
            return False, images
        
        return False, []
    
    def format_gallery_caption(self, title: str, platform: str, description: str = "",
                              image_count: int = 0, index: int = 0, total: int = 0,
                              is_premium: bool = False) -> str:
        """Format caption for gallery message"""
        caption = f"🖼️ {title}\n\n"
        caption += f"📱 Platform: {platform.upper()}\n"
        
        if image_count > 0:
            caption += f"🎨 Gallery: {image_count} images\n"
        
        if is_premium and description:
            caption += f"📝 {description[:100]}...\n\n"
        
        if total > 0:
            caption += f"📊 Item {index+1}/{total}"
        
        return caption[:1024]  # Telegram caption limit
    
    def extract_images_from_description(self, description: str) -> List[str]:
        """Extract image URLs from description text"""
        if not description:
            return []
        
        # Find all image URLs in description
        image_patterns = [
            r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp)',
            r'https?://i\.redd\.it/[^\s]+',
            r'https?://i\.imgur\.com/[^\s]+',
            r'https?://preview\.redd\.it/[^\s]+'
        ]
        
        images = []
        for pattern in image_patterns:
            urls = re.findall(pattern, description)
            images.extend(urls)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_images = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)
        
        return unique_images[:self.max_images_per_gallery]
    
    def create_media_group(self, images: List[str], caption: str = "") -> List[Dict]:
        """
        Create media group for Telegram
        
        Returns list of InputMediaPhoto objects data
        """
        media_group = []
        
        for i, image_url in enumerate(images[:self.max_images_per_gallery]):
            media_item = {
                'type': 'photo',
                'media': image_url,
                'caption': caption if i == 0 else ""  # Only first image gets caption
            }
            media_group.append(media_item)
        
        return media_group
    
    def get_gallery_info(self, url: str, platform: str, content_dict: Dict = None) -> Dict:
        """
        Get comprehensive gallery information
        
        Returns:
            {
                'is_gallery': bool,
                'image_count': int,
                'images': List[str],
                'thumbnail': str,
                'has_multiple_images': bool
            }
        """
        info = {
            'is_gallery': False,
            'image_count': 0,
            'images': [],
            'thumbnail': None,
            'has_multiple_images': False
        }
        
        try:
            # Check if gallery
            is_gallery = self.is_gallery_url(url)
            info['is_gallery'] = is_gallery
            
            if is_gallery:
                # Get images
                images = self.get_gallery_images(url, platform, content_dict)
                images = self.clean_image_urls(images)
                
                info['images'] = images
                info['image_count'] = len(images)
                info['has_multiple_images'] = len(images) >= 2
                
                if images:
                    info['thumbnail'] = images[0]
            
            # Fallback: check for single image
            elif content_dict:
                thumbnail = content_dict.get('thumbnail')
                if thumbnail and self.validate_image_url(thumbnail):
                    info['images'] = [thumbnail]
                    info['thumbnail'] = thumbnail
                    info['image_count'] = 1
        
        except Exception as e:
            logging.error(f"Error getting gallery info: {e}")
        
        return info
