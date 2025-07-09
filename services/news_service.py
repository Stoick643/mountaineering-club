"""
News service for managing news curation and AI content.
"""
from datetime import datetime
import logging

from models import db, News, HistoricalEvent
from ai_services.news_curator import NewsCurator
from ai_services.content_generator_sqlalchemy import HistoricalEventGenerator
from ai_services.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)


class NewsService:
    """Service for handling news curation and AI content generation."""
    
    def __init__(self, ai_client=None):
        """
        Initialize the news service.
        
        Args:
            ai_client: AI client instance (optional, creates new DeepSeekClient if not provided)
        """
        self.ai_client = ai_client or DeepSeekClient()
        self.news_curator = NewsCurator(db, News, self.ai_client)
        self.historical_generator = HistoricalEventGenerator(db, HistoricalEvent, self.ai_client)
    
    def get_latest_news(self, limit=5, category=None):
        """
        Get latest curated news articles.
        
        Args:
            limit (int): Number of articles to return
            category (str): Category filter (optional)
            
        Returns:
            list: List of news articles
        """
        try:
            return self.news_curator.get_latest_news(limit=limit, category=category)
        except Exception as e:
            logger.error(f"Error getting latest news: {e}")
            return []
    
    def get_news_by_category(self):
        """
        Get news grouped by all categories.
        
        Returns:
            dict: News articles grouped by category
        """
        try:
            return self.news_curator.get_news_by_category()
        except Exception as e:
            logger.error(f"Error getting news by categories: {e}")
            return {}
    
    def update_news_feed(self):
        """
        Manually trigger news update (admin only).
        
        Returns:
            tuple: (success: bool, message: str, stats: dict)
        """
        try:
            stats = self.news_curator.fetch_and_process_feeds()
            return True, 'News feed updated successfully', stats
        except Exception as e:
            logger.error(f"Error updating news feed: {e}")
            return False, 'Failed to update news feed', {}
    
    def get_news_statistics(self):
        """
        Get news curation statistics.
        
        Returns:
            dict: News statistics
        """
        try:
            return self.news_curator.get_statistics()
        except Exception as e:
            logger.error(f"Error getting news stats: {e}")
            return {}
    
    def get_today_historical_event(self, date=None):
        """
        Get historical event for today or specific date.
        
        Args:
            date (str): Date in MM-DD format (optional, uses today if not provided)
            
        Returns:
            dict or None: Historical event data
        """
        try:
            event = self.historical_generator.get_today_event(date)
            return event
        except Exception as e:
            logger.error(f"Error getting today's historical event: {e}")
            return None
    
    def get_random_historical_event(self):
        """
        Get a random historical event.
        
        Returns:
            dict or None: Historical event data
        """
        try:
            event = self.historical_generator.get_random_event()
            return event
        except Exception as e:
            logger.error(f"Error getting random historical event: {e}")
            return None
    
    def get_featured_historical_events(self, limit=5):
        """
        Get featured historical events.
        
        Args:
            limit (int): Number of events to return
            
        Returns:
            list: List of featured historical events
        """
        try:
            events = self.historical_generator.get_featured_events(limit=limit)
            return events
        except Exception as e:
            logger.error(f"Error getting featured historical events: {e}")
            return []
    
    def get_historical_events_by_category(self, category, limit=10):
        """
        Get historical events by category.
        
        Args:
            category (str): Event category
            limit (int): Number of events to return
            
        Returns:
            list: List of historical events
        """
        try:
            events = self.historical_generator.get_events_by_category(category, limit)
            return events
        except Exception as e:
            logger.error(f"Error getting events by category {category}: {e}")
            return []
    
    def search_historical_events(self, query, limit=10):
        """
        Search historical events.
        
        Args:
            query (str): Search query
            limit (int): Number of events to return
            
        Returns:
            list: List of matching historical events
        """
        try:
            events = self.historical_generator.search_events(query, limit)
            return events
        except Exception as e:
            logger.error(f"Error searching historical events: {e}")
            return []
    
    def verify_historical_event(self, event_id):
        """
        Mark historical event as verified (admin only).
        
        Args:
            event_id (int): Event ID to verify
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            success = self.historical_generator.verify_event(event_id)
            if success:
                return True, 'Event verified successfully'
            else:
                return False, 'Event not found'
        except Exception as e:
            logger.error(f"Error verifying event {event_id}: {e}")
            return False, 'Failed to verify event'
    
    def feature_historical_event(self, event_id):
        """
        Mark historical event as featured (admin only).
        
        Args:
            event_id (int): Event ID to feature
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            success = self.historical_generator.mark_as_featured(event_id)
            if success:
                return True, 'Event marked as featured'
            else:
                return False, 'Event not found'
        except Exception as e:
            logger.error(f"Error featuring event {event_id}: {e}")
            return False, 'Failed to feature event'
    
    def generate_historical_events_range(self, start_date, end_date):
        """
        Generate historical events for date range (admin only).
        
        Args:
            start_date (str): Start date in MM-DD format
            end_date (str): End date in MM-DD format
            
        Returns:
            tuple: (success: bool, message: str, count: int)
        """
        try:
            count = self.historical_generator.generate_events_for_date_range(start_date, end_date)
            return True, f'Generated {count} historical events', count
        except Exception as e:
            logger.error(f"Error generating event range: {e}")
            return False, 'Failed to generate events', 0
    
    def get_historical_events_statistics(self):
        """
        Get statistics about historical events.
        
        Returns:
            dict: Historical events statistics
        """
        try:
            stats = self.historical_generator.get_statistics()
            return stats
        except Exception as e:
            logger.error(f"Error getting historical events stats: {e}")
            return {}
    
    def is_ai_available(self):
        """
        Check if AI services are available.
        
        Returns:
            bool: True if AI is available, False otherwise
        """
        return self.ai_client.is_available()
    
    def test_ai_connection(self):
        """
        Test AI connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            return self.ai_client.test_connection()
        except Exception as e:
            logger.error(f"Error testing AI connection: {e}")
            return False