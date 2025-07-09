"""
Simple News Curator - Clean and lightweight news aggregation
Fetches RSS feeds and stores articles in database with optional AI enhancement.
"""

import logging
import feedparser
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse
from .config import NEWS_SOURCES, RELEVANCE_THRESHOLD, MAX_DAILY_ARTICLES

logger = logging.getLogger(__name__)

class NewsCurator:
    """Simple news curator that fetches RSS feeds and stores articles"""
    
    def __init__(self, db, News, ai_client=None):
        self.db = db
        self.News = News
        self.ai_client = ai_client
        self.relevance_threshold = RELEVANCE_THRESHOLD
        self.max_articles = MAX_DAILY_ARTICLES
    
    def fetch_and_process_feeds(self) -> Dict:
        """
        Fetch RSS feeds and store articles in database
        
        Returns:
            Dict: Simple processing stats
        """
        logger.info("Starting simple news curation")
        
        stats = {
            'feeds_processed': 0,
            'articles_found': 0,
            'articles_stored': 0,
            'errors': []
        }
        
        # Track articles per source for balancing (max 2 per source)
        source_article_count = {}
        
        # Process Slovenian feeds first (priority), then international
        slovenian_feeds = NEWS_SOURCES.get('regional', [])
        international_feeds = NEWS_SOURCES.get('international', [])
        safety_feeds = NEWS_SOURCES.get('safety', [])
        
        # Process in priority order: Slovenian → International → Safety
        feed_priority = slovenian_feeds + international_feeds + safety_feeds
        
        # Process each feed with source balancing
        for feed_url in feed_priority:
            try:
                logger.info(f"Fetching feed: {feed_url}")
                feed = feedparser.parse(feed_url)
                
                if feed.bozo:
                    logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
                
                stats['feeds_processed'] += 1
                
                # Get source name for balancing
                source_name = self._get_source_name(feed_url)
                
                # Initialize source counter
                if source_name not in source_article_count:
                    source_article_count[source_name] = 0
                
                # Process articles with source limit (max 2 per source)
                articles_from_source = 0
                max_per_source = 2
                
                for entry in feed.entries:
                    # Stop if we've reached the limit for this source
                    if articles_from_source >= max_per_source:
                        break
                    
                    if self._process_article(entry, feed_url):
                        stats['articles_stored'] += 1
                        articles_from_source += 1
                        source_article_count[source_name] += 1
                        
                    stats['articles_found'] += 1
                
                logger.info(f"Processed {len(feed.entries)} articles from {feed_url} (stored: {articles_from_source})")
                
            except Exception as e:
                error_msg = f"Error processing feed {feed_url}: {str(e)}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
        
        # Log source distribution
        logger.info(f"Source distribution: {source_article_count}")
        
        # Clean up old articles (keep only last 30 days)
        self._cleanup_old_articles()
        
        logger.info(f"News curation completed: {stats}")
        return stats
    
    def _process_article(self, entry, feed_url: str) -> bool:
        """
        Process a single article from RSS feed
        
        Args:
            entry: RSS entry object
            feed_url: Source feed URL
            
        Returns:
            bool: True if article was stored, False if skipped
        """
        try:
            # Extract basic article info
            title = entry.get('title', '').strip()
            url = entry.get('link', '').strip()
            
            if not title or not url:
                return False
            
            # Check if article already exists
            existing = self.News.query.filter_by(original_url=url).first()
            if existing:
                return False
            
            # Get article content/summary
            content = self._get_article_content(entry)
            
            # Determine source name from feed URL
            source_name = self._get_source_name(feed_url)
            
            # Get published date
            published_at = self._get_published_date(entry)
            
            # Detect original language from source
            detected_language = self._detect_language(source_name)
            
            # Optional AI enhancement
            summary = None
            relevance_score = 7.0  # Default score (above threshold when AI disabled)
            category = 'general'
            
            if self.ai_client and self.ai_client.is_available():
                try:
                    # Get AI summary in original language (no translation)
                    summary = self.ai_client.summarize_news_article(
                        title=title,
                        content=content,
                        language=detected_language,
                        max_length=150
                    )
                    
                    # Get relevance score
                    relevance_score = self.ai_client.calculate_relevance_score(
                        title=title,
                        content=content
                    )
                    
                    # Simple category detection
                    category = self._detect_category(title, content)
                    
                except Exception as e:
                    logger.warning(f"AI processing failed for {title}: {e}")
            
            # Skip articles with low relevance
            if relevance_score < self.relevance_threshold:
                logger.info(f"Skipping article with low relevance ({relevance_score}): {title}")
                return False
            
            # Create and store article
            article = self.News(
                title=title,
                summary=summary or content[:200] + "..." if len(content) > 200 else content,
                original_url=url,
                source_name=source_name,
                relevance_score=relevance_score,
                language=detected_language,
                category=category,
                published_at=published_at,
                created_at=datetime.utcnow()
            )
            
            self.db.session.add(article)
            self.db.session.commit()
            
            logger.info(f"Stored article: {title} (score: {relevance_score})")
            return True
            
        except Exception as e:
            logger.error(f"Error processing article {entry.get('title', 'Unknown')}: {e}")
            self.db.session.rollback()
            return False
    
    def _get_article_content(self, entry) -> str:
        """Extract content from RSS entry"""
        # Try different content fields
        content = entry.get('description', '')
        if not content:
            content = entry.get('summary', '')
        if not content:
            content = entry.get('content', [{}])[0].get('value', '') if entry.get('content') else ''
        
        return content.strip()
    
    def _get_source_name(self, feed_url: str) -> str:
        """Extract source name from feed URL"""
        domain = urlparse(feed_url).netloc
        # Simple mapping of common domains
        source_mapping = {
            'climbing.com': 'Climbing Magazine',
            'alpinist.com': 'Alpinist',
            'planetmountain.com': 'PlanetMountain',
            'outsideonline.com': 'Outside Magazine',
            'rockandice.com': 'Rock & Ice',
            'desnivel.com': 'Desnivel',
            '8a.nu': '8a.nu',
            'plezanje.net': 'Plezanje.net',
            'gore-ljudje.net': 'Gore-Ljudje',
            'planinci.si': 'Planinci.si',
            'gore-in-ljudje.net': 'Gore in Ljudje',
            'hribi.net': 'Hribi.net',
            'avalanche.si': 'Avalanche.si',
            'meteo.arso.gov.si': 'ARSO',
            'avalanche.org': 'Avalanche.org',
            'mountain-rescue.org': 'Mountain Rescue'
        }
        return source_mapping.get(domain, domain)
    
    def _get_published_date(self, entry) -> Optional[datetime]:
        """Extract published date from RSS entry"""
        for date_field in ['published_parsed', 'updated_parsed']:
            if hasattr(entry, date_field) and getattr(entry, date_field):
                try:
                    time_struct = getattr(entry, date_field)
                    return datetime(*time_struct[:6])
                except:
                    pass
        return datetime.utcnow()
    
    def _detect_language(self, source_name: str) -> str:
        """Detect language based on source"""
        # Slovenian sources
        slovenian_sources = ['Gore-Ljudje', 'Plezanje.net', 'Planinci.si', 'Gore in Ljudje', 'Hribi.net', 'Avalanche.si', 'ARSO']
        
        # Spanish sources
        spanish_sources = ['Desnivel']
        
        if any(sl_source in source_name for sl_source in slovenian_sources):
            return 'sl'
        elif any(es_source in source_name for es_source in spanish_sources):
            return 'es'
        else:
            return 'en'
    
    def _detect_category(self, title: str, content: str) -> str:
        """Simple category detection based on keywords"""
        text = (title + ' ' + content).lower()
        
        # Simple keyword matching
        if any(word in text for word in ['varnost', 'nesreča', 'reševanje', 'safety', 'accident']):
            return 'safety'
        elif any(word in text for word in ['oprema', 'equipment', 'gear']):
            return 'equipment'
        elif any(word in text for word in ['slovenija', 'slovenia', 'alpe', 'triglav']):
            return 'local'
        elif any(word in text for word in ['dosežek', 'achievement', 'rekord', 'record']):
            return 'achievement'
        elif any(word in text for word in ['odprava', 'expedition', 'himalaja']):
            return 'expedition'
        else:
            return 'general'
    
    def _cleanup_old_articles(self):
        """Remove articles older than 30 days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            old_articles = self.News.query.filter(self.News.created_at < cutoff_date).all()
            
            for article in old_articles:
                self.db.session.delete(article)
            
            if old_articles:
                self.db.session.commit()
                logger.info(f"Cleaned up {len(old_articles)} old articles")
        except Exception as e:
            logger.error(f"Error cleaning up old articles: {e}")
            self.db.session.rollback()
    
    def get_latest_news(self, limit: int = 5, category: str = None) -> List[Dict]:
        """
        Get latest curated news articles with priority system:
        1. At least 3 new articles daily (from current day)
        2. Max 5 articles total
        3. Fill with old articles if needed
        4. New articles have priority
        """
        # Get today's start time
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Build base query with category filter if specified
        base_query = self.News.query
        if category:
            base_query = base_query.filter_by(category=category)
        
        # Get today's articles first (priority)
        today_articles = base_query.filter(
            self.News.created_at >= today_start
        ).order_by(
            self.News.relevance_score.desc(),
            self.News.created_at.desc()
        ).all()
        
        # If we have enough from today, just return top articles
        if len(today_articles) >= limit:
            return [article.to_dict() for article in today_articles[:limit]]
        
        # Otherwise, fill remaining slots with older articles
        older_articles = base_query.filter(
            self.News.created_at < today_start
        ).order_by(
            self.News.relevance_score.desc(),
            self.News.created_at.desc()
        ).limit(limit - len(today_articles)).all()
        
        # Combine: today's articles first, then older articles
        combined = today_articles + older_articles
        return [article.to_dict() for article in combined[:limit]]
    
    def get_news_by_category(self) -> Dict[str, List[Dict]]:
        """Get news grouped by category"""
        categories = ['local', 'safety', 'equipment', 'achievement', 'expedition', 'general']
        result = {}
        
        for category in categories:
            articles = self.News.query.filter_by(category=category).order_by(
                self.News.relevance_score.desc(),
                self.News.created_at.desc()
            ).limit(3).all()
            
            result[category] = [article.to_dict() for article in articles]
        
        return result
    
    def get_statistics(self) -> Dict:
        """Get simple statistics about news collection"""
        total_articles = self.News.query.count()
        recent_articles = self.News.query.filter(
            self.News.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        return {
            'total_articles': total_articles,
            'recent_articles': recent_articles,
            'last_updated': datetime.utcnow().isoformat()
        }