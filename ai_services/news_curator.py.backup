"""
News Curation Service
Aggregates, filters and curates mountaineering news using AI.
"""

import logging
import feedparser
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse
import re
from .deepseek_client import DeepSeekClient
from .config import NEWS_SOURCES, RELEVANCE_THRESHOLD, MAX_DAILY_ARTICLES

logger = logging.getLogger(__name__)

class NewsCurator:
    """Curates mountaineering news from RSS feeds using AI"""
    
    def __init__(self, db, News, deepseek_client: DeepSeekClient = None):
        self.db = db
        self.News = News
        self.ai_client = deepseek_client or DeepSeekClient()
        self.relevance_threshold = RELEVANCE_THRESHOLD
        self.max_articles = MAX_DAILY_ARTICLES
    
    def fetch_and_process_feeds(self) -> Dict:
        """
        Main curation pipeline: fetch RSS feeds, process with AI, store results
        
        Returns:
            Dict: Summary of processing results
        """
        logger.info("Starting news curation process")
        
        stats = {
            'feeds_processed': 0,
            'articles_found': 0,
            'articles_processed': 0,
            'articles_stored': 0,
            'errors': []
        }
        
        # Fetch articles from all RSS sources
        all_articles = []
        
        for source_type, feeds in NEWS_SOURCES.items():
            for feed_url in feeds:
                try:
                    articles = self._fetch_feed(feed_url, source_type)
                    all_articles.extend(articles)
                    stats['feeds_processed'] += 1
                    stats['articles_found'] += len(articles)
                    logger.info(f"Fetched {len(articles)} articles from {feed_url}")
                    
                except Exception as e:
                    error_msg = f"Error fetching {feed_url}: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
        
        # Remove duplicates
        unique_articles = self._remove_duplicates(all_articles)
        logger.info(f"Found {len(unique_articles)} unique articles after deduplication")
        
        # Process articles with AI
        processed_articles = []
        
        for article in unique_articles[:50]:  # Limit to avoid API costs
            try:
                processed = self._process_article_with_ai(article)
                if processed:
                    processed_articles.append(processed)
                    stats['articles_processed'] += 1
                    
            except Exception as e:
                error_msg = f"Error processing article {article.get('title', 'Unknown')}: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
        
        # Filter by relevance and store
        relevant_articles = [a for a in processed_articles if a['relevance_score'] >= self.relevance_threshold]
        
        # Sort by relevance score and limit to max articles
        relevant_articles.sort(key=lambda x: x['relevance_score'], reverse=True)
        top_articles = relevant_articles[:self.max_articles]
        
        for article in top_articles:
            try:
                if self._store_article(article):
                    stats['articles_stored'] += 1
                    
            except Exception as e:
                error_msg = f"Error storing article {article.get('title', 'Unknown')}: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
        
        # Clean up old articles
        self._cleanup_old_articles()
        
        logger.info(f"News curation completed: {stats['articles_stored']} articles stored")
        return stats
    
    def _fetch_feed(self, feed_url: str, source_type: str) -> List[Dict]:
        """Fetch and parse RSS feed"""
        
        try:
            # Add user agent to avoid blocking
            headers = {
                'User-Agent': 'Mountaineering Club News Curator 1.0'
            }
            
            response = requests.get(feed_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            articles = []
            for entry in feed.entries:
                # Extract article data
                article = {
                    'title': self._clean_text(entry.get('title', '')),
                    'link': entry.get('link', ''),
                    'description': self._clean_text(entry.get('description', '')),
                    'published': self._parse_date(entry.get('published')),
                    'source_name': feed.feed.get('title', urlparse(feed_url).netloc),
                    'source_type': source_type,
                    'raw_content': entry.get('summary', '')
                }
                
                # Skip if essential data missing
                if article['title'] and article['link']:
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")
            return []
    
    def _remove_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles by URL and similar titles"""
        
        seen_urls = set()
        seen_titles = set()
        unique_articles = []
        
        for article in articles:
            url = article['link']
            title = article['title'].lower().strip()
            
            # Skip if URL already seen
            if url in seen_urls:
                continue
            
            # Skip if very similar title already seen
            title_words = set(title.split())
            is_similar = False
            
            for seen_title in seen_titles:
                seen_words = set(seen_title.split())
                # If 80% of words overlap, consider it duplicate
                if len(title_words & seen_words) / max(len(title_words), len(seen_words)) > 0.8:
                    is_similar = True
                    break
            
            if not is_similar:
                seen_urls.add(url)
                seen_titles.add(title)
                unique_articles.append(article)
        
        return unique_articles
    
    def _process_article_with_ai(self, article: Dict) -> Optional[Dict]:
        """Process article with AI for relevance scoring and summarization"""
        
        if not self.ai_client.is_available():
            logger.warning("AI client not available, skipping AI processing")
            return None
        
        try:
            # Calculate relevance score
            club_interests = ['alpinizem', 'plezanje', 'gorništvo', 'varnost', 'oprema', 'julijske alpe', 'slovenija']
            relevance_score = self.ai_client.calculate_relevance_score(
                article['title'], 
                article['description'], 
                club_interests
            )
            
            # Skip if not relevant enough
            if relevance_score < self.relevance_threshold:
                logger.debug(f"Article '{article['title'][:50]}...' scored {relevance_score}, below threshold")
                return None
            
            # Generate summary in Slovenian
            summary = self.ai_client.summarize_news_article(
                article['title'], 
                article['description'], 
                language='sl',
                max_length=200
            )
            
            # Categorize content
            category = self._categorize_article(article['title'], article['description'])
            
            processed_article = {
                'title': article['title'],
                'summary': summary or article['description'][:200] + '...',
                'original_url': article['link'],
                'source_name': article['source_name'],
                'relevance_score': relevance_score,
                'language': 'sl',
                'category': category,
                'published_at': article['published'],
                'source_type': article['source_type']
            }
            
            logger.info(f"Processed article: {article['title'][:50]}... (score: {relevance_score})")
            return processed_article
            
        except Exception as e:
            logger.error(f"AI processing failed for article: {e}")
            return None
    
    def _categorize_article(self, title: str, content: str) -> str:
        """Categorize article based on content"""
        
        text = (title + ' ' + content).lower()
        
        # Local/regional content gets highest priority
        local_keywords = ['slovenia', 'slovenija', 'alps', 'triglav', 'julian', 'kamnik', 'ljubljana']
        if any(keyword in text for keyword in local_keywords):
            return 'local'
        
        # Safety-related content
        safety_keywords = ['avalanche', 'rescue', 'accident', 'safety', 'weather', 'conditions', 'warning']
        if any(keyword in text for keyword in safety_keywords):
            return 'safety'
        
        # Equipment and gear
        equipment_keywords = ['gear', 'equipment', 'review', 'boots', 'rope', 'harness', 'helmet', 'technology']
        if any(keyword in text for keyword in equipment_keywords):
            return 'equipment'
        
        # Achievements and first ascents
        achievement_keywords = ['first ascent', 'record', 'summit', 'achievement', 'breakthrough', 'milestone']
        if any(keyword in text for keyword in achievement_keywords):
            return 'achievement'
        
        # Expeditions
        expedition_keywords = ['expedition', 'climb', 'attempt', 'team', 'mountain', 'peak']
        if any(keyword in text for keyword in expedition_keywords):
            return 'expedition'
        
        return 'general'
    
    def _store_article(self, article_data: Dict) -> bool:
        """Store article in database"""
        
        try:
            # Check if article already exists
            existing = self.News.query.filter_by(original_url=article_data['original_url']).first()
            if existing:
                logger.debug(f"Article already exists: {article_data['title'][:50]}...")
                return False
            
            # Create new news entry
            news_article = self.News(
                title=article_data['title'],
                summary=article_data['summary'],
                original_url=article_data['original_url'],
                source_name=article_data['source_name'],
                relevance_score=article_data['relevance_score'],
                language=article_data['language'],
                category=article_data['category'],
                is_featured=article_data['relevance_score'] >= 8.0,  # Auto-feature high relevance
                published_at=article_data['published_at'],
                created_at=datetime.utcnow()
            )
            
            self.db.session.add(news_article)
            self.db.session.commit()
            
            logger.info(f"Stored article: {article_data['title'][:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store article: {e}")
            self.db.session.rollback()
            return False
    
    def _cleanup_old_articles(self, days_old: int = 30):
        """Remove articles older than specified days"""
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            old_articles = self.News.query.filter(self.News.created_at < cutoff_date).all()
            
            for article in old_articles:
                self.db.session.delete(article)
            
            self.db.session.commit()
            logger.info(f"Cleaned up {len(old_articles)} old articles")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old articles: {e}")
            self.db.session.rollback()
    
    def get_latest_news(self, limit: int = 5, category: str = None) -> List[Dict]:
        """Get latest curated news articles"""
        
        query = self.News.query
        
        if category:
            query = query.filter_by(category=category)
        
        articles = query.order_by(
            self.News.relevance_score.desc(),
            self.News.created_at.desc()
        ).limit(limit).all()
        
        return [article.to_dict() for article in articles]
    
    def get_news_by_category(self) -> Dict[str, List[Dict]]:
        """Get news grouped by category"""
        
        categories = ['local', 'safety', 'equipment', 'achievement', 'expedition']
        result = {}
        
        for category in categories:
            articles = self.News.query.filter_by(
                category=category
            ).order_by(
                self.News.relevance_score.desc()
            ).limit(3).all()
            
            result[category] = [article.to_dict() for article in articles]
        
        return result
    
    def get_statistics(self) -> Dict:
        """Get news curation statistics"""
        
        total_articles = self.News.query.count()
        featured_articles = self.News.query.filter_by(is_featured=True).count()
        
        # Articles by category
        category_stats = {}
        categories = ['local', 'safety', 'equipment', 'achievement', 'expedition', 'general']
        
        for category in categories:
            count = self.News.query.filter_by(category=category).count()
            category_stats[category] = count
        
        # Recent articles (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_articles = self.News.query.filter(self.News.created_at >= week_ago).count()
        
        return {
            'total_articles': total_articles,
            'featured_articles': featured_articles,
            'recent_articles': recent_articles,
            'category_breakdown': category_stats,
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean HTML tags and normalize text"""
        
        if not text:
            return ''
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        import html
        text = html.unescape(text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse publication date from RSS feed"""
        
        if not date_str:
            return None
        
        try:
            # Try parsing with feedparser's time module
            import time
            time_struct = feedparser._parse_date(date_str)
            if time_struct:
                return datetime(*time_struct[:6])
        except:
            pass
        
        # Fallback to current time
        return datetime.utcnow()