const axios = require('axios');
const cron = require('node-cron');
const { Client } = require('pg');
const redis = require('redis');
require('dotenv').config();

class ContentAggregator {
    constructor() {
        this.db = new Client({ 
            connectionString: process.env.DATABASE_URL,
            ssl: { rejectUnauthorized: false }
        });
        this.redis = redis.createClient({ 
            url: process.env.REDIS_URL,
            socket: { tls: true, rejectUnauthorized: false }
        });
        this.categories = {
            'memes': { 
                subreddits: ['memes', 'dankmemes', 'funny', 'comedyheaven'], 
                keywords: ['meme', 'funny', 'humor', 'joke', 'lol', 'comedy']
            },
            'sports': { 
                subreddits: ['sports', 'soccer','PremierLeague', 'LaLiga', 'Bundesliga', 'seriea', 'championsleague', 'football', 'Boxing', 'tennis', 'MMA', 'ufc', 'nba', 'nfl', 'cricket', ], 
                keywords: ['football', 'basketball', 'sports', 'boxing', 'fight', 'game', 'match', 'player', 'team', 'premier league', 'la liga', 'bundesliga', 'serie a', 'champions league', 'uefa', 'fifa', 'world cup', 'messi', 'ronaldo', 'goal', 'transfer', 'mma', 'ufc', 'knockout', 'fighter']
            },
            'entertainment': { 
                subreddits: ['music', 'movies', 'television', 'dance'], 
                keywords: ['music', 'dance', 'movie', 'celebrity', 'artist', 'singer']
            },
            'gaming': { 
                subreddits: ['gaming', 'pcgaming', 'nintendo', 'xbox', 'playstation'], 
                keywords: ['game', 'gaming', 'esports', 'steam', 'twitch']
            },
            'tech': { 
                subreddits: ['technology', 'programming', 'gadgets', 'apple'], 
                keywords: ['tech', 'software', 'AI', 'programming', 'gadget']
            },
            'jobs': {
                subreddits: ['forhire', 'freelance', 'remotework'],
                keywords: ['freelance', 'remote', 'upwork', 'fiverr', 'contract', 'gig', 'work from home', 'freelancer']
            },
            'news': { 
                subreddits: ['news', 'worldnews', 'politics'], 
                keywords: ['news', 'breaking', 'politics', 'world']
            }
        };
    }

    async init() {
        await this.db.connect();
        try {
            await this.redis.connect();
            this.redis.on('error', (err) => {
                console.error('Redis error:', err.message);
            });
            console.log('Redis connected');
        } catch (err) {
            console.error('Redis connection failed:', err.message);
            console.log('Continuing without Redis cache...');
            this.redis = null;
        }
        console.log('Aggregator initialized');
    }

    async fetchRedditTrends(subreddit, category) {
        try {
            const response = await axios.get(`https://www.reddit.com/r/${subreddit}/hot.json`, {
                params: { limit: 15 },
                headers: { 'User-Agent': 'TrendLensBot/1.0' }
            });
            
            const posts = response.data.data.children;
            
            for (const post of posts) {
                const data = post.data;
                const engagement = data.score + data.num_comments;
                const trendScore = this.calculateTrendScore(data.score, data.num_comments, data.created_utc);
                
                await this.storeContent({
                    platform: 'reddit',
                    category,
                    title: data.title,
                    url: `https://reddit.com${data.permalink}`,
                    thumbnail: data.thumbnail !== 'self' && data.thumbnail !== 'default' ? data.thumbnail : null,
                    description: data.selftext?.substring(0, 200) || `${data.score} upvotes | ${data.num_comments} comments`,
                    engagement_score: engagement,
                    trend_score: trendScore
                });
            }
        } catch (error) {
            console.error(`Reddit fetch error for ${subreddit}:`, error.message);
        }
    }

    async fetchYouTubeTrends(category, keywords) {
        try {
            // Trending videos
            const trendingRes = await axios.get('https://www.googleapis.com/youtube/v3/videos', {
                params: {
                    part: 'snippet,statistics',
                    chart: 'mostPopular',
                    regionCode: 'US',
                    maxResults: 15,
                    key: process.env.YOUTUBE_API_KEY
                }
            });

            for (const video of trendingRes.data.items) {
                const stats = video.statistics;
                const engagement = parseInt(stats.viewCount) + parseInt(stats.likeCount || 0) + parseInt(stats.commentCount || 0);
                const trendScore = this.calculateTrendScore(
                    parseInt(stats.viewCount), 
                    parseInt(stats.likeCount || 0), 
                    new Date(video.snippet.publishedAt).getTime() / 1000
                );

                await this.storeContent({
                    platform: 'youtube',
                    category,
                    title: video.snippet.title,
                    url: `https://youtube.com/watch?v=${video.id}`,
                    thumbnail: video.snippet.thumbnails.medium.url,
                    description: `${video.snippet.channelTitle} | ${stats.viewCount} views | ${stats.likeCount || 0} likes | ${stats.commentCount || 0} comments`,
                    engagement_score: engagement,
                    trend_score: trendScore
                });
            }

            // Category-specific search
            if (keywords && keywords.length > 0) {
                const searchRes = await axios.get('https://www.googleapis.com/youtube/v3/search', {
                    params: {
                        part: 'snippet',
                        q: keywords.join(' OR '),
                        type: 'video',
                        order: 'viewCount',
                        publishedAfter: new Date(Date.now() - 48*60*60*1000).toISOString(),
                        maxResults: 10,
                        key: process.env.YOUTUBE_API_KEY
                    }
                });

                for (const item of searchRes.data.items) {
                    await this.storeContent({
                        platform: 'youtube',
                        category,
                        title: item.snippet.title,
                        url: `https://youtube.com/watch?v=${item.id.videoId}`,
                        thumbnail: item.snippet.thumbnails.medium.url,
                        description: item.snippet.channelTitle,
                        engagement_score: 1000,
                        trend_score: this.calculateTrendScore(1000, 100, new Date(item.snippet.publishedAt).getTime() / 1000)
                    });
                }
            }
        } catch (error) {
            console.error('YouTube fetch error:', error.message);
        }
    }

    async fetchTwitterTrends(category, keywords) {
        try {
            const response = await axios.get('https://api.twitter.com/2/tweets/search/recent', {
                headers: { 'Authorization': `Bearer ${process.env.TWITTER_BEARER_TOKEN}` },
                params: {
                    query: keywords.join(' OR ') + ' -is:retweet',
                    'tweet.fields': 'public_metrics,created_at,author_id',
                    'user.fields': 'username',
                    expansions: 'author_id',
                    max_results: 20,
                    sort_order: 'relevancy'
                }
            });

            if (response.data.data) {
                for (const tweet of response.data.data) {
                    const metrics = tweet.public_metrics;
                    const engagement = metrics.retweet_count + metrics.like_count + metrics.reply_count;
                    const author = response.data.includes?.users?.find(u => u.id === tweet.author_id);
                    
                    await this.storeContent({
                        platform: 'twitter',
                        category,
                        title: tweet.text.substring(0, 100),
                        url: `https://twitter.com/${author?.username}/status/${tweet.id}`,
                        thumbnail: null,
                        description: `${metrics.retweet_count} retweets | ${metrics.like_count} likes | ${metrics.reply_count} replies`,
                        engagement_score: engagement,
                        trend_score: this.calculateTrendScore(engagement, metrics.like_count, new Date(tweet.created_at).getTime() / 1000)
                    });
                }
            }
        } catch (error) {
            console.error('Twitter fetch error:', error.message);
        }
    }

    async fetchTikTokTrends(category, keywords) {
        if (process.env.TIKTOK_SCRAPE_ENABLED !== 'true') return;
        
        try {
            // Use RapidAPI TikTok Scraper
            const response = await axios.get('https://tiktok-scraper7.p.rapidapi.com/feed/trending', {
                headers: {
                    'X-RapidAPI-Key': process.env.RAPIDAPI_TIKTOK_KEY,
                    'X-RapidAPI-Host': process.env.RAPIDAPI_TIKTOK_HOST || 'tiktok-scraper7.p.rapidapi.com'
                },
                params: {
                    count: 20,
                    region: 'US'
                },
                timeout: parseInt(process.env.TIKTOK_REQUEST_TIMEOUT || 10000)
            });

            if (response.data && response.data.data) {
                for (const item of response.data.data) {
                    const stats = item.stats || {};
                    const engagement = (stats.playCount || 0) + (stats.diggCount || 0) + (stats.commentCount || 0) + (stats.shareCount || 0);
                    
                    await this.storeContent({
                        platform: 'tiktok',
                        category,
                        title: item.desc || item.title || 'TikTok Video',
                        url: item.webVideoUrl || `https://www.tiktok.com/@${item.author?.uniqueId}/video/${item.id}`,
                        thumbnail: item.video?.cover || item.video?.dynamicCover,
                        description: `@${item.author?.uniqueId || 'tiktok'} | ${stats.playCount || 0} plays | ${stats.diggCount || 0} likes | ${stats.commentCount || 0} comments`,
                        engagement_score: engagement,
                        trend_score: this.calculateTrendScore(stats.playCount || 1000, stats.diggCount || 100, item.createTime || Date.now() / 1000)
                    });
                }
            }
        } catch (error) {
            console.error('TikTok RapidAPI fetch error:', error.message);
            // Fallback to basic scraping if RapidAPI fails
            if (error.response?.status === 429) {
                console.log('Rate limit hit, skipping TikTok for now');
                return;
            }
        }
    }

    async fetchInstagramTrends(category, hashtags) {
        try {
            // Using Instagram Graph API
            const response = await axios.get(`https://graph.instagram.com/ig_hashtag_search`, {
                params: {
                    user_id: process.env.INSTAGRAM_USER_ID,
                    q: hashtags[0],
                    access_token: process.env.INSTAGRAM_ACCESS_TOKEN
                }
            });

            if (response.data.data && response.data.data[0]) {
                const hashtagId = response.data.data[0].id;
                const mediaRes = await axios.get(`https://graph.instagram.com/${hashtagId}/top_media`, {
                    params: {
                        user_id: process.env.INSTAGRAM_USER_ID,
                        fields: 'id,caption,media_type,media_url,permalink,like_count,comments_count',
                        access_token: process.env.INSTAGRAM_ACCESS_TOKEN
                    }
                });

                for (const media of mediaRes.data.data || []) {
                    const engagement = (media.like_count || 0) + (media.comments_count || 0);
                    
                    await this.storeContent({
                        platform: 'instagram',
                        category,
                        title: media.caption?.substring(0, 100) || 'Instagram Post',
                        url: media.permalink,
                        thumbnail: media.media_url,
                        description: `${media.like_count || 0} likes | ${media.comments_count || 0} comments`,
                        engagement_score: engagement,
                        trend_score: this.calculateTrendScore(engagement, media.like_count || 0, Date.now() / 1000)
                    });
                }
            }
        } catch (error) {
            console.error('Instagram fetch error:', error.message);
        }
    }

    async fetchNews(category) {
        try {
            // Fetch from specific news sources
            const sources = ['bbc-news', 'cnn', 'al-jazeera-english', 'reuters', 'the-guardian-uk', 'associated-press', 'bloomberg', 'the-washington-post', 'the-new-york-times'];
            
            for (const source of sources) {
                try {
                    const response = await axios.get('https://newsapi.org/v2/top-headlines', {
                        params: {
                            sources: source,
                            pageSize: 5,
                            apiKey: process.env.NEWS_API_KEY
                        }
                    });

                    for (const article of response.data.articles || []) {
                        const trendScore = this.calculateTrendScore(1000, 100, new Date(article.publishedAt).getTime() / 1000);

                        await this.storeContent({
                            platform: 'news',
                            category: 'news',
                            title: article.title,
                            url: article.url,
                            thumbnail: article.urlToImage,
                            description: `${source.toUpperCase()} | ${article.description || ''}`,
                            engagement_score: 1000,
                            trend_score: trendScore
                        });
                    }
                } catch (err) {
                    console.error(`Failed to fetch from ${source}:`, err.message);
                }
            }
            
            // Also fetch general top headlines
            const generalResponse = await axios.get('https://newsapi.org/v2/top-headlines', {
                params: {
                    country: 'us',
                    category: category === 'tech' ? 'technology' : 'general',
                    pageSize: 10,
                    apiKey: process.env.NEWS_API_KEY
                }
            });

            for (const article of generalResponse.data.articles || []) {
                const trendScore = this.calculateTrendScore(1000, 100, new Date(article.publishedAt).getTime() / 1000);

                await this.storeContent({
                    platform: 'news',
                    category,
                    title: article.title,
                    url: article.url,
                    thumbnail: article.urlToImage,
                    description: article.description,
                    engagement_score: 1000,
                    trend_score: trendScore
                });
            }
        } catch (error) {
            console.error('News fetch error:', error.message);
        }
    }

    calculateTrendScore(engagement, secondary, timestamp) {
        try {
            // Validate inputs
            const eng = parseFloat(engagement) || 0;
            const sec = parseFloat(secondary) || 0;
            const ts = parseFloat(timestamp) || (Date.now() / 1000);
            
            // Ensure positive values
            if (eng < 0 || sec < 0 || ts < 0) return 0;
            
            const now = Date.now() / 1000;
            const age = Math.max(0, now - ts);
            const freshness = Math.max(0, 1 - (age / 86400)); // 24 hours decay
            
            const score = (Math.log(eng + 1) * 0.7 + Math.log(sec + 1) * 0.3) * freshness;
            
            // Return 0 if NaN or invalid
            return isNaN(score) || !isFinite(score) ? 0 : Math.max(0, score);
        } catch (error) {
            console.error('Trend score calculation error:', error.message);
            return 0;
        }
    }

    async storeContent(content) {
        try {
            const crypto = require('crypto');
            
            // Generate content hash for deduplication
            const normalizedTitle = content.title.toLowerCase().trim().replace(/[^a-z0-9]/g, '');
            const contentHash = crypto.createHash('sha256')
                .update(normalizedTitle + content.category)
                .digest('hex');
            
            // Check for duplicate by hash
            const duplicateCheck = await this.db.query(
                'SELECT id FROM content WHERE content_hash = $1 AND category = $2 LIMIT 1',
                [contentHash, content.category]
            );
            
            if (duplicateCheck.rows.length > 0) {
                // Duplicate found, skip
                return;
            }
            
            const query = `
                INSERT INTO content (platform, category, title, url, thumbnail, description, engagement_score, trend_score, content_hash, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                ON CONFLICT (url) DO UPDATE SET
                    engagement_score = EXCLUDED.engagement_score,
                    trend_score = EXCLUDED.trend_score
            `;
            
            await this.db.query(query, [
                content.platform, content.category, content.title, content.url,
                content.thumbnail, content.description, content.engagement_score, 
                content.trend_score, contentHash
            ]);

            // Cache trending content
            if (this.redis && this.redis.isOpen) {
                try {
                    await this.redis.zAdd(`trending:${content.category}`, {
                        score: content.trend_score,
                        value: JSON.stringify(content)
                    });
                } catch (e) {
                    // Silent fail for Redis
                }
            }
        } catch (error) {
            if (!error.message.includes('duplicate key')) {
                console.error('Store content error:', error.message);
            }
        }
    }

    async fetchFreelanceJobs() {
        try {
            // Fetch job-related content from Twitter mentioning Upwork/Fiverr
            const platforms = ['upwork', 'fiverr'];
            for (const platform of platforms) {
                const response = await axios.get('https://api.twitter.com/2/tweets/search/recent', {
                    headers: { 'Authorization': `Bearer ${process.env.TWITTER_BEARER_TOKEN}` },
                    params: {
                        query: `${platform} (hiring OR job OR freelance) -is:retweet`,
                        'tweet.fields': 'public_metrics,created_at',
                        max_results: 10
                    }
                });

                if (response.data.data) {
                    for (const tweet of response.data.data) {
                        const metrics = tweet.public_metrics;
                        await this.storeContent({
                            platform: platform,
                            category: 'jobs',
                            title: tweet.text.substring(0, 100),
                            url: `https://twitter.com/i/status/${tweet.id}`,
                            thumbnail: null,
                            description: `${platform.charAt(0).toUpperCase() + platform.slice(1)} opportunity | ${metrics.like_count} likes`,
                            engagement_score: metrics.like_count + metrics.retweet_count,
                            trend_score: this.calculateTrendScore(metrics.like_count, metrics.retweet_count, new Date(tweet.created_at).getTime() / 1000)
                        });
                    }
                }
            }
        } catch (error) {
            console.error('Freelance jobs fetch error:', error.message);
        }
    }

    async aggregateContent() {
        console.log('Starting content aggregation...');
        
        for (const [category, config] of Object.entries(this.categories)) {
            console.log(`Fetching ${category}...`);
            
            // Fetch Reddit content
            for (const subreddit of config.subreddits) {
                await this.fetchRedditTrends(subreddit, category);
            }
            
            // Skip failing APIs
            if (process.env.YOUTUBE_API_KEY) await this.fetchYouTubeTrends(category, config.keywords);
            if (process.env.TWITTER_BEARER_TOKEN) await this.fetchTwitterTrends(category, config.keywords);
            if (process.env.RAPIDAPI_TIKTOK_KEY) await this.fetchTikTokTrends(category, config.keywords);
            if (process.env.INSTAGRAM_ACCESS_TOKEN) await this.fetchInstagramTrends(category, config.keywords);
            
            // Fetch freelance jobs from Upwork/Fiverr mentions
            if (category === 'jobs' && process.env.TWITTER_BEARER_TOKEN) await this.fetchFreelanceJobs();
            
            // Fetch news
            await this.fetchNews(category);
            
            // Clean old content (older than 48 hours)
            await this.cleanOldContent(category);
        }
        
        console.log('Content aggregation completed');
    }

    async cleanOldContent(category) {
        try {
            const cutoff = new Date(Date.now() - 48*60*60*1000);
            await this.db.query(
                'DELETE FROM content WHERE category = $1 AND created_at < $2',
                [category, cutoff]
            );
            if (this.redis && this.redis.isOpen) {
                await this.redis.del(`trending:${category}`);
            }
        } catch (error) {
            console.error('Clean old content error:', error.message);
        }
    }

    startScheduler() {
        // Hot categories (sports, news) - every 2 minutes for real-time updates
        cron.schedule('*/2 * * * *', () => {
            console.log('Fetching hot categories...');
            this.aggregateCategory('sports');
            this.aggregateCategory('news');
        });
        
        // Regular categories - every 10 minutes for faster updates
        cron.schedule('*/10 * * * *', () => {
            this.aggregateContent();
        });
        
        // Initial run
        this.aggregateContent();
    }

    async aggregateCategory(category) {
        const config = this.categories[category];
        if (!config) return;
        
        console.log(`Quick fetch: ${category}`);
        
        for (const subreddit of config.subreddits) {
            await this.fetchRedditTrends(subreddit, category);
        }
        if (process.env.YOUTUBE_API_KEY) await this.fetchYouTubeTrends(category, config.keywords);
        if (process.env.TWITTER_BEARER_TOKEN) await this.fetchTwitterTrends(category, config.keywords);
        if (process.env.RAPIDAPI_TIKTOK_KEY) await this.fetchTikTokTrends(category, config.keywords);
        if (category === 'jobs' && process.env.TWITTER_BEARER_TOKEN) await this.fetchFreelanceJobs();
        if (process.env.NEWS_API_KEY) await this.fetchNews(category);
    }
}

const aggregator = new ContentAggregator();
aggregator.init().then(() => {
    aggregator.startScheduler();
    
    // Express server for on-demand fetching
    const express = require('express');
    const app = express();
    
    app.get('/fetch/:category', async (req, res) => {
        const category = req.params.category;
        console.log(`On-demand fetch requested: ${category}`);
        await aggregator.aggregateCategory(category);
        res.json({ status: 'success', category });
    });
    
    app.listen(3000, () => console.log('Aggregator API on port 3000'));
});