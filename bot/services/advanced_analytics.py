"""
Advanced Analytics Service
Handles quality scoring, trending algorithms, and content analysis
"""

from database import SessionLocal, Content, User, UserInteraction
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)


class AdvancedAnalytics:
    """Advanced analytics and content scoring"""
    
    # Quality keywords by category
    QUALITY_KEYWORDS = {
        'memes': ['viral', 'trending', 'hilarious', 'funny', 'epic', 'legendary', 'savage'],
        'sports': ['goal', 'win', 'champion', 'record', 'highlight', 'amazing', 'incredible'],
        'tech': ['breakthrough', 'innovation', 'revolutionary', 'advanced', 'cutting-edge', 'new'],
        'gaming': ['epic', 'legendary', 'pro', 'insane', 'clutch', 'gameplay', 'tournament'],
        'entertainment': ['exclusive', 'premiere', 'official', 'trailer', 'release', 'announcement'],
        'news': ['breaking', 'exclusive', 'confirmed', 'official', 'update', 'latest'],
        'jobs': ['hiring', 'remote', 'salary', 'benefits', 'urgent', 'immediate']
    }
    
    # Blocked keywords (spam/low quality)
    BLOCKED_KEYWORDS = [
        'clickbait', 'fake', 'scam', 'spam', 'bot', 'advertisement',
        'buy now', 'limited time', 'act now', 'free money'
    ]
    
    @staticmethod
    def calculate_trending_score(content: Content) -> float:
        """
        Calculate comprehensive trending score for content
        
        Factors:
        - Engagement score (40%)
        - Recency (30%)
        - Quality keywords (20%)
        - Platform weight (10%)
        
        Returns:
            Score from 0-100
        """
        try:
            score = 0.0
            
            # 1. Engagement Score (40%)
            engagement = content.engagement_score or 0
            engagement_normalized = min(engagement / 1000, 1.0)  # Normalize to 0-1
            score += engagement_normalized * 40
            
            # 2. Recency Score (30%)
            if content.created_at:
                age_hours = (datetime.now(timezone.utc) - content.created_at).total_seconds() / 3600
                # Exponential decay: newer = higher score
                recency_score = max(0, 1 - (age_hours / 168))  # 168 hours = 1 week
                score += recency_score * 30
            
            # 3. Quality Keywords (20%)
            quality_score = AdvancedAnalytics.calculate_quality_score(content)
            score += (quality_score / 100) * 20
            
            # 4. Platform Weight (10%)
            platform_weights = {
                'reddit': 1.0,
                'twitter': 0.9,
                'youtube': 1.0,
                'tiktok': 0.8,
                'instagram': 0.8,
                'facebook': 0.7
            }
            platform = content.platform.lower() if content.platform else 'unknown'
            platform_weight = platform_weights.get(platform, 0.5)
            score += platform_weight * 10
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"Error calculating trending score: {e}")
            return 50.0  # Default score
    
    @staticmethod
    def calculate_quality_score(content: Content) -> float:
        """
        Calculate content quality score
        
        Factors:
        - Quality keywords presence
        - Title length and structure
        - Description quality
        - No blocked keywords
        - Category relevance
        
        Returns:
            Score from 0-100
        """
        try:
            score = 50.0  # Base score
            
            text = f"{content.title} {content.description or ''}".lower()
            
            # 1. Quality Keywords (+30 max)
            category = content.category.lower() if content.category else ''
            quality_keywords = AdvancedAnalytics.QUALITY_KEYWORDS.get(category, [])
            
            keyword_matches = sum(1 for kw in quality_keywords if kw in text)
            score += min(keyword_matches * 5, 30)
            
            # 2. Title Quality (+10)
            if content.title:
                title_length = len(content.title)
                if 20 <= title_length <= 100:  # Optimal length
                    score += 10
                elif 10 <= title_length <= 150:  # Acceptable
                    score += 5
            
            # 3. Description Quality (+10)
            if content.description:
                desc_length = len(content.description)
                if desc_length >= 50:  # Has description
                    score += 10
                elif desc_length >= 20:
                    score += 5
            
            # 4. Blocked Keywords (-50)
            blocked_found = sum(1 for kw in AdvancedAnalytics.BLOCKED_KEYWORDS if kw in text)
            if blocked_found > 0:
                score -= blocked_found * 25
            
            # 5. Category Relevance (+10)
            if AdvancedAnalytics.validate_category_content(content):
                score += 10
            
            return max(0, min(score, 100.0))
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 50.0
    
    @staticmethod
    def validate_category_content(content: Content) -> bool:
        """
        Validate if content matches its category
        
        Returns:
            True if content is relevant to category
        """
        try:
            if not content.category:
                return False
            
            category = content.category.lower()
            text = f"{content.title} {content.description or ''}".lower()
            
            # Category-specific keywords
            category_keywords = {
                'memes': ['meme', 'funny', 'humor', 'joke', 'lol', 'comedy'],
                'sports': ['sport', 'game', 'match', 'player', 'team', 'league', 'football', 'basketball'],
                'tech': ['tech', 'technology', 'software', 'hardware', 'ai', 'computer', 'digital'],
                'gaming': ['game', 'gaming', 'player', 'esports', 'console', 'pc'],
                'entertainment': ['movie', 'music', 'show', 'celebrity', 'entertainment', 'film'],
                'news': ['news', 'report', 'update', 'breaking', 'announce'],
                'jobs': ['job', 'hiring', 'career', 'work', 'position', 'employment']
            }
            
            keywords = category_keywords.get(category, [])
            matches = sum(1 for kw in keywords if kw in text)
            
            return matches > 0
            
        except Exception as e:
            logger.error(f"Error validating category: {e}")
            return True  # Default to valid
    
    @staticmethod
    def deduplicate_content(contents: List[Content]) -> List[Content]:
        """
        Remove duplicate content based on URL and title similarity
        
        Returns:
            Deduplicated list of content
        """
        try:
            seen_urls = set()
            seen_titles = set()
            unique_contents = []
            
            for content in contents:
                # Normalize URL
                url = AdvancedAnalytics._normalize_url(content.url)
                
                # Normalize title
                title = AdvancedAnalytics._normalize_title(content.title)
                
                # Check if duplicate
                if url not in seen_urls and title not in seen_titles:
                    seen_urls.add(url)
                    seen_titles.add(title)
                    unique_contents.append(content)
            
            return unique_contents
            
        except Exception as e:
            logger.error(f"Error deduplicating content: {e}")
            return contents
    
    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL for comparison"""
        if not url:
            return ""
        
        # Remove protocol
        url = re.sub(r'^https?://', '', url)
        # Remove www
        url = re.sub(r'^www\.', '', url)
        # Remove trailing slash
        url = url.rstrip('/')
        # Remove query parameters
        url = url.split('?')[0]
        
        return url.lower()
    
    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize title for comparison"""
        if not title:
            return ""
        
        # Remove special characters
        title = re.sub(r'[^\w\s]', '', title)
        # Remove extra spaces
        title = ' '.join(title.split())
        # Convert to lowercase
        title = title.lower()
        
        return title
    
    @staticmethod
    def sort_by_trending(contents: List[Content]) -> List[Content]:
        """
        Sort content by trending score
        
        Returns:
            Sorted list (highest score first)
        """
        try:
            # Calculate scores for all content
            scored_contents = []
            for content in contents:
                score = AdvancedAnalytics.calculate_trending_score(content)
                scored_contents.append((content, score))
            
            # Sort by score (descending)
            scored_contents.sort(key=lambda x: x[1], reverse=True)
            
            # Return sorted content
            return [content for content, score in scored_contents]
            
        except Exception as e:
            logger.error(f"Error sorting by trending: {e}")
            return contents
    
    @staticmethod
    def filter_quality_content(contents: List[Content], min_quality: int = 30) -> List[Content]:
        """
        Filter content by minimum quality score
        
        Args:
            contents: List of content to filter
            min_quality: Minimum quality score (0-100)
            
        Returns:
            Filtered list of high-quality content
        """
        try:
            quality_contents = []
            
            for content in contents:
                quality_score = AdvancedAnalytics.calculate_quality_score(content)
                if quality_score >= min_quality:
                    quality_contents.append(content)
            
            return quality_contents
            
        except Exception as e:
            logger.error(f"Error filtering quality content: {e}")
            return contents
    
    @staticmethod
    def is_content_fresh(content: Content, max_age_hours: int = 48) -> bool:
        """
        Check if content is fresh (recent)
        
        Args:
            content: Content to check
            max_age_hours: Maximum age in hours
            
        Returns:
            True if content is fresh
        """
        try:
            if not content.created_at:
                return False
            
            age = datetime.now(timezone.utc) - content.created_at
            age_hours = age.total_seconds() / 3600
            
            return age_hours <= max_age_hours
            
        except Exception as e:
            logger.error(f"Error checking content freshness: {e}")
            return True  # Default to fresh
    
    @staticmethod
    def get_trending_categories() -> List[Dict[str, Any]]:
        """
        Get trending categories with statistics
        
        Returns:
            List of categories with view counts and trends
        """
        db = SessionLocal()
        try:
            # Get views per category in last 24 hours
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            
            categories = ['memes', 'sports', 'tech', 'gaming', 'entertainment', 'news', 'jobs']
            trending = []
            
            for category in categories:
                # Count views
                views = db.query(UserInteraction).join(Content).filter(
                    Content.category == category,
                    UserInteraction.action == 'view',
                    UserInteraction.timestamp >= cutoff
                ).count()
                
                # Count content
                content_count = db.query(Content).filter(
                    Content.category == category,
                    Content.created_at >= cutoff
                ).count()
                
                trending.append({
                    'category': category,
                    'views': views,
                    'content_count': content_count,
                    'avg_views_per_content': views / content_count if content_count > 0 else 0
                })
            
            # Sort by views
            trending.sort(key=lambda x: x['views'], reverse=True)
            
            return trending
            
        except Exception as e:
            logger.error(f"Error getting trending categories: {e}")
            return []
        finally:
            db.close()
    
    @staticmethod
    def get_user_engagement_stats(user_id: int) -> Dict[str, Any]:
        """
        Get detailed user engagement statistics
        
        Returns:
            Dictionary with engagement metrics
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {}
            
            # Total interactions
            total_views = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id,
                UserInteraction.action == 'view'
            ).count()
            
            total_saves = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id,
                UserInteraction.action == 'save'
            ).count()
            
            # Recent activity (last 7 days)
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            recent_views = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id,
                UserInteraction.action == 'view',
                UserInteraction.timestamp >= cutoff
            ).count()
            
            # Favorite category
            category_views = db.query(
                Content.category,
                db.func.count(UserInteraction.id).label('count')
            ).join(UserInteraction).filter(
                UserInteraction.user_id == user_id,
                UserInteraction.action == 'view'
            ).group_by(Content.category).order_by(db.text('count DESC')).first()
            
            favorite_category = category_views[0] if category_views else 'None'
            
            # Engagement rate
            save_rate = (total_saves / total_views * 100) if total_views > 0 else 0
            
            return {
                'total_views': total_views,
                'total_saves': total_saves,
                'recent_views': recent_views,
                'favorite_category': favorite_category,
                'save_rate': save_rate,
                'is_active': recent_views > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting user engagement stats: {e}")
            return {}
        finally:
            db.close()
    
    @staticmethod
    def recalculate_all_scores() -> Tuple[int, int]:
        """
        Recalculate trending and quality scores for all content
        
        Returns:
            Tuple of (updated_count, error_count)
        """
        db = SessionLocal()
        try:
            contents = db.query(Content).all()
            updated = 0
            errors = 0
            
            for content in contents:
                try:
                    # Calculate new scores
                    trending_score = AdvancedAnalytics.calculate_trending_score(content)
                    quality_score = AdvancedAnalytics.calculate_quality_score(content)
                    
                    # Update content
                    content.trend_score = trending_score
                    # Store quality score if column exists
                    if hasattr(content, 'quality_score'):
                        content.quality_score = quality_score
                    
                    updated += 1
                    
                except Exception as e:
                    logger.error(f"Error updating content {content.id}: {e}")
                    errors += 1
            
            db.commit()
            return (updated, errors)
            
        except Exception as e:
            logger.error(f"Error recalculating scores: {e}")
            db.rollback()
            return (0, 0)
        finally:
            db.close()
