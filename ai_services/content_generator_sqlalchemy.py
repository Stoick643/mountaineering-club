"""
Historical Event Content Generator (SQLAlchemy Version)
Generates and manages historical mountaineering events for "Na Današnji Dan" feature.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .deepseek_client import DeepSeekClient
from .config import DEFAULT_LANGUAGE, EVENT_CATEGORIES

logger = logging.getLogger(__name__)

class HistoricalEventGenerator:
    """Generates and manages historical mountaineering events using SQLAlchemy"""
    
    def __init__(self, db, HistoricalEvent, deepseek_client: DeepSeekClient = None):
        self.db = db
        self.HistoricalEvent = HistoricalEvent
        self.ai_client = deepseek_client or DeepSeekClient()
    
    def get_today_event(self, date: str = None) -> Optional[Dict]:
        """
        Get historical event for today or specific date
        
        Args:
            date (str): Date in MM-DD format, defaults to today
            
        Returns:
            Dict: Historical event or None
        """
        
        if not date:
            date = datetime.now().strftime("%m-%d")
        
        # Try to get existing event from database
        event = self.HistoricalEvent.query.filter_by(date=date).first()
        
        if event:
            logger.info(f"Found existing event for {date}: {event.title}")
            return event.to_dict()
        
        # Generate new event with AI if none exists
        if self.ai_client.is_available():
            logger.info(f"Generating new historical event for {date}")
            return self._generate_and_store_event(date)
        
        # Fallback to predefined events if AI unavailable
        return self._get_fallback_event(date)
    
    def _generate_and_store_event(self, date: str) -> Optional[Dict]:
        """Generate new event with AI and store in database"""
        
        ai_event = self.ai_client.generate_historical_event(date, DEFAULT_LANGUAGE)
        
        if not ai_event:
            logger.error(f"AI failed to generate event for {date}")
            return self._get_fallback_event(date)
        
        # Create new event
        try:
            new_event = self.HistoricalEvent(
                date=date,
                year=ai_event.get('year'),
                title=ai_event.get('title'),
                description=ai_event.get('description'),
                location=ai_event.get('location'),
                people=ai_event.get('people', []),
                category=ai_event.get('category', 'achievement'),
                reference_url=ai_event.get('reference_url'),
                source='AI-generated',
                language=DEFAULT_LANGUAGE,
                is_featured=True,
                is_verified=False,  # Manual verification needed
                created_at=datetime.utcnow()
            )
            
            self.db.session.add(new_event)
            self.db.session.commit()
            
            logger.info(f"Stored new AI-generated event for {date}")
            return new_event.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
            self.db.session.rollback()
            return None
    
    def _get_fallback_event(self, date: str) -> Optional[Dict]:
        """Get fallback event when AI is unavailable"""
        
        # Try to get any existing event for this date
        existing_event = self.HistoricalEvent.query.filter_by(date=date).first()
        if existing_event:
            return existing_event.to_dict()
        
        # Generate simple fallback
        try:
            fallback_event = self.HistoricalEvent(
                date=date,
                year=2024,
                title='Dan planinstva',
                description='Danes se spomnimo na bogato tradicijo alpinizma in planinarstva.',
                location='Globalno',
                people=[],
                category='achievement',
                source='fallback',
                language=DEFAULT_LANGUAGE,
                is_featured=False,
                is_verified=True,
                created_at=datetime.utcnow()
            )
            
            self.db.session.add(fallback_event)
            self.db.session.commit()
            
            logger.info(f"Created fallback event for {date}")
            return fallback_event.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to create fallback event: {e}")
            self.db.session.rollback()
            return None
    
    def get_events_by_category(self, category: str, limit: int = 10) -> List[Dict]:
        """Get events by category"""
        
        events = self.HistoricalEvent.query.filter_by(
            category=category
        ).order_by(self.HistoricalEvent.created_at.desc()).limit(limit).all()
        
        return [event.to_dict() for event in events]
    
    def get_random_event(self) -> Optional[Dict]:
        """Get a random historical event"""
        
        # SQLAlchemy doesn't have a direct random function, so we'll use a simple approach
        import random
        
        total_events = self.HistoricalEvent.query.count()
        if total_events == 0:
            return None
        
        random_offset = random.randint(0, total_events - 1)
        event = self.HistoricalEvent.query.offset(random_offset).first()
        
        return event.to_dict() if event else None
    
    def search_events(self, query: str, limit: int = 10) -> List[Dict]:
        """Search events by text"""
        
        events = self.HistoricalEvent.query.filter(
            self.HistoricalEvent.title.contains(query) |
            self.HistoricalEvent.description.contains(query) |
            self.HistoricalEvent.location.contains(query)
        ).limit(limit).all()
        
        return [event.to_dict() for event in events]
    
    def get_featured_events(self, limit: int = 5) -> List[Dict]:
        """Get featured historical events"""
        
        events = self.HistoricalEvent.query.filter_by(
            is_featured=True
        ).order_by(self.HistoricalEvent.created_at.desc()).limit(limit).all()
        
        return [event.to_dict() for event in events]
    
    def mark_as_featured(self, event_id: int) -> bool:
        """Mark event as featured"""
        
        try:
            event = self.HistoricalEvent.query.get(event_id)
            if event:
                event.is_featured = True
                self.db.session.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to mark event as featured: {e}")
            self.db.session.rollback()
            return False
    
    def verify_event(self, event_id: int) -> bool:
        """Mark event as manually verified"""
        
        try:
            event = self.HistoricalEvent.query.get(event_id)
            if event:
                event.is_verified = True
                self.db.session.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to verify event: {e}")
            self.db.session.rollback()
            return False
    
    def generate_events_for_date_range(self, start_date: str, end_date: str) -> int:
        """
        Generate events for a date range (useful for initial population)
        
        Args:
            start_date (str): Start date in MM-DD format
            end_date (str): End date in MM-DD format
            
        Returns:
            int: Number of events generated
        """
        
        if not self.ai_client.is_available():
            logger.error("AI client not available for bulk generation")
            return 0
        
        generated_count = 0
        
        # Convert to datetime objects for iteration
        start_month, start_day = map(int, start_date.split('-'))
        end_month, end_day = map(int, end_date.split('-'))
        
        start_dt = datetime(2024, start_month, start_day)
        end_dt = datetime(2024, end_month, end_day)
        
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%m-%d")
            
            # Skip if event already exists
            existing = self.HistoricalEvent.query.filter_by(date=date_str).first()
            if not existing:
                event_dict = self._generate_and_store_event(date_str)
                if event_dict:
                    generated_count += 1
                    logger.info(f"Generated event {generated_count} for {date_str}")
                
                # Small delay to avoid API rate limits
                import time
                time.sleep(1)
            
            current_dt += timedelta(days=1)
        
        logger.info(f"Generated {generated_count} historical events")
        return generated_count
    
    def get_statistics(self) -> Dict:
        """Get statistics about historical events collection"""
        
        total_events = self.HistoricalEvent.query.count()
        ai_generated = self.HistoricalEvent.query.filter_by(source='AI-generated').count()
        featured_events = self.HistoricalEvent.query.filter_by(is_featured=True).count()
        verified_events = self.HistoricalEvent.query.filter_by(is_verified=True).count()
        
        # Category breakdown
        category_stats = {}
        for category in EVENT_CATEGORIES:
            count = self.HistoricalEvent.query.filter_by(category=category).count()
            category_stats[category] = count
        
        return {
            'total_events': total_events,
            'ai_generated': ai_generated,
            'featured_events': featured_events,
            'verified_events': verified_events,
            'category_breakdown': category_stats,
            'last_updated': datetime.utcnow().isoformat()
        }