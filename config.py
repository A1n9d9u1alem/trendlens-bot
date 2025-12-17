CATEGORIES = {
    'memes': {
        'subreddits': ['memes', 'dankmemes', 'funny', 'wholesomememes'],
        'keywords': ['meme', 'funny', 'comedy'],
        'icon': '😂',
        'update_frequency': 30  # minutes
    },
    'sports': {
        'subreddits': ['sports', 'soccer', 'nba', 'nfl', 'cricket', 'tennis'],
        'keywords': ['football', 'basketball', 'sports'],
        'icon': '⚽',
        'update_frequency': 5  # minutes - FAST for live events
    },
    'tech': {
        'subreddits': ['technology', 'programming', 'gadgets', 'android', 'apple'],
        'keywords': ['tech', 'software', 'hardware', 'apple'],
        'icon': '💻',
        'update_frequency': 30
    },
    'gaming': {
        'subreddits': ['gaming', 'pcgaming', 'ps5', 'xbox', 'nintendo'],
        'keywords': ['game', 'gaming', 'esports'],
        'icon': '🎮',
        'update_frequency': 30
    },
    'entertainment': {
        'subreddits': ['movies', 'music', 'television', 'entertainment'],
        'keywords': ['movie', 'music', 'celebrity'],
        'icon': '🎬',
        'update_frequency': 30
    },
    'news': {
        'subreddits': ['news', 'worldnews', 'politics'],
        'keywords': ['news', 'breaking', 'politics', 'update'],
        'icon': '📰',
        'update_frequency': 5  # minutes - FAST for breaking news
    }
}

TIER_LIMITS = {
    'free': {
        'daily_requests': 10,
        'content_per_request': 5,
        'categories': 3,
        'media_preview': False,
        'realtime_fetch': False
    },
    'premium': {
        'daily_requests': -1,  # Unlimited
        'content_per_request': 20,
        'categories': -1,  # All
        'media_preview': True,
        'realtime_fetch': True  # Instant updates on demand
    }
}

PRICING = {
    'monthly': 499,  # $4.99 in cents
    'yearly': 4999   # $49.99 in cents
}