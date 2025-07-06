"""
Historical Event Content Generator
Generates and manages historical mountaineering events for "Na Današnji Dan" feature.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pymongo import MongoClient
from .deepseek_client import DeepSeekClient
from .config import DEFAULT_LANGUAGE, EVENT_CATEGORIES

logger = logging.getLogger(__name__)

class HistoricalEventGenerator:
    """Generates and manages historical mountaineering events"""
    
    def __init__(self, mongo_db, deepseek_client: DeepSeekClient = None):
        self.db = mongo_db
        self.ai_client = deepseek_client or DeepSeekClient()
        self.collection = self.db.historical_events
        
        # Ensure indexes for efficient queries
        self.collection.create_index("date")
        self.collection.create_index("category")
        self.collection.create_index("is_featured")
    
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
        event = self.collection.find_one({"date": date})
        
        if event:
            logger.info(f"Found existing event for {date}: {event['title']}")
            return event
        
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
        
        # Prepare event for database
        event_data = {
            'date': date,
            'year': ai_event.get('year'),
            'title': ai_event.get('title'),
            'description': ai_event.get('description'),
            'location': ai_event.get('location'),
            'people': ai_event.get('people', []),
            'category': ai_event.get('category', 'achievement'),
            'source': 'AI-generated',
            'language': DEFAULT_LANGUAGE,
            'created_at': datetime.utcnow(),
            'is_featured': True,
            'is_verified': False  # Manual verification needed
        }
        
        try:
            result = self.collection.insert_one(event_data)
            event_data['_id'] = result.inserted_id
            logger.info(f"Stored new AI-generated event for {date}")
            return event_data
            
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
            return None
    
    def _get_fallback_event(self, date: str) -> Optional[Dict]:
        """Get fallback event when AI is unavailable"""
        
        # Try to get any existing event for this date
        existing_event = self.collection.find_one({"date": date})
        if existing_event:
            return existing_event
        
        # Generate simple fallback
        fallback_event = {
            'date': date,
            'year': 2024,
            'title': 'Dan planinstva',
            'description': 'Danes se spomnimo na bogato tradicijo alpinizma in planinarstva.',
            'location': 'Globalno',
            'people': [],
            'category': 'achievement',
            'source': 'fallback',
            'language': DEFAULT_LANGUAGE,
            'created_at': datetime.utcnow(),
            'is_featured': False,
            'is_verified': True
        }
        
        try:
            result = self.collection.insert_one(fallback_event)
            fallback_event['_id'] = result.inserted_id
            logger.info(f"Created fallback event for {date}")
            return fallback_event
            
        except Exception as e:
            logger.error(f"Failed to create fallback event: {e}")
            return None
    
    def get_events_by_category(self, category: str, limit: int = 10) -> List[Dict]:
        """Get events by category"""
        
        return list(self.collection.find(
            {"category": category}
        ).sort("created_at", -1).limit(limit))
    
    def get_random_event(self) -> Optional[Dict]:
        """Get a random historical event"""
        
        pipeline = [{"$sample": {"size": 1}}]
        events = list(self.collection.aggregate(pipeline))
        
        return events[0] if events else None
    
    def search_events(self, query: str, limit: int = 10) -> List[Dict]:
        """Search events by text"""
        
        return list(self.collection.find({
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"location": {"$regex": query, "$options": "i"}}
            ]
        }).limit(limit))
    
    def get_featured_events(self, limit: int = 5) -> List[Dict]:
        """Get featured historical events"""
        
        return list(self.collection.find(
            {"is_featured": True}
        ).sort("created_at", -1).limit(limit))
    
    def mark_as_featured(self, event_id: str) -> bool:
        """Mark event as featured"""
        
        try:
            from bson import ObjectId
            result = self.collection.update_one(
                {"_id": ObjectId(event_id)},
                {"$set": {"is_featured": True}}
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to mark event as featured: {e}")
            return False
    
    def verify_event(self, event_id: str) -> bool:
        """Mark event as manually verified"""
        
        try:
            from bson import ObjectId
            result = self.collection.update_one(
                {"_id": ObjectId(event_id)},
                {"$set": {"is_verified": True}}
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to verify event: {e}")
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
            if not self.collection.find_one({"date": date_str}):
                event = self._generate_and_store_event(date_str)
                if event:
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
        
        total_events = self.collection.count_documents({})
        ai_generated = self.collection.count_documents({"source": "AI-generated"})
        featured_events = self.collection.count_documents({"is_featured": True})
        verified_events = self.collection.count_documents({"is_verified": True})
        
        # Category breakdown
        category_stats = {}
        for category in EVENT_CATEGORIES:
            count = self.collection.count_documents({"category": category})
            category_stats[category] = count
        
        return {
            'total_events': total_events,
            'ai_generated': ai_generated,
            'featured_events': featured_events,
            'verified_events': verified_events,
            'category_breakdown': category_stats,
            'last_updated': datetime.utcnow().isoformat()
        }