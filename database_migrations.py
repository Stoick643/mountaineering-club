#!/usr/bin/env python3
"""
Database Migration Script for AI Content Features
Sets up collections and indexes for historical events and news curation.
"""

import json
import logging
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_env():
    """Load environment variables from .env file if available"""
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()

def connect_to_mongodb():
    """Connect to MongoDB using environment variables"""
    try:
        mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/mountaineering_club')
        client = MongoClient(mongo_uri)
        
        # Test connection
        client.admin.command('ping')
        db = client.get_database()
        
        logger.info(f"✅ Connected to MongoDB")
        return db
    
    except Exception as e:
        logger.error(f"❌ Error connecting to MongoDB: {e}")
        raise

def create_historical_events_collection(db):
    """Create and configure historical_events collection"""
    
    collection_name = 'historical_events'
    
    try:
        # Create collection if it doesn't exist
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
            logger.info(f"✅ Created collection: {collection_name}")
        else:
            logger.info(f"📄 Collection {collection_name} already exists")
        
        collection = db[collection_name]
        
        # Create indexes for efficient queries
        indexes = [
            ("date", 1),                    # For daily lookups
            ("category", 1),                # For category filtering
            ("is_featured", 1),             # For featured events
            ("is_verified", 1),             # For verified events
            ("created_at", -1),             # For chronological ordering
            ([("title", "text"), ("description", "text")], None)  # For text search
        ]
        
        for index_spec in indexes:
            if isinstance(index_spec, tuple) and len(index_spec) == 2:
                if index_spec[1] is None:  # Text index
                    collection.create_index(index_spec[0])
                    logger.info(f"✅ Created text index on {collection_name}")
                else:
                    collection.create_index(index_spec[0], unique=False)
                    logger.info(f"✅ Created index on {collection_name}.{index_spec[0]}")
        
        # Create unique compound index for date
        collection.create_index("date", unique=True)
        logger.info(f"✅ Created unique index on {collection_name}.date")
        
        return collection
        
    except Exception as e:
        logger.error(f"❌ Error creating {collection_name} collection: {e}")
        raise

def create_news_articles_collection(db):
    """Create and configure news_articles collection"""
    
    collection_name = 'news_articles'
    
    try:
        # Create collection if it doesn't exist
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
            logger.info(f"✅ Created collection: {collection_name}")
        else:
            logger.info(f"📄 Collection {collection_name} already exists")
        
        collection = db[collection_name]
        
        # Create indexes for efficient queries
        indexes = [
            ("published_at", -1),           # For chronological ordering
            ("category", 1),                # For category filtering
            ("relevance_score", -1),        # For relevance ranking
            ("is_featured", 1),             # For featured articles
            ("source", 1),                  # For source filtering
            ("region", 1),                  # For geographic filtering
            ([("title_sl", "text"), ("summary_sl", "text")], None)  # For text search
        ]
        
        for index_spec in indexes:
            if isinstance(index_spec, tuple) and len(index_spec) == 2:
                if index_spec[1] is None:  # Text index
                    collection.create_index(index_spec[0])
                    logger.info(f"✅ Created text index on {collection_name}")
                else:
                    collection.create_index(index_spec[0], unique=False)
                    logger.info(f"✅ Created index on {collection_name}.{index_spec[0]}")
        
        # Create unique compound index for URL and published date
        collection.create_index([("original_url", 1), ("published_at", 1)], unique=True)
        logger.info(f"✅ Created unique compound index on {collection_name}")
        
        return collection
        
    except Exception as e:
        logger.error(f"❌ Error creating {collection_name} collection: {e}")
        raise

def seed_historical_events(collection):
    """Seed historical events collection with initial data"""
    
    try:
        # Check if collection already has data
        if collection.count_documents({}) > 0:
            logger.info("📊 Historical events collection already has data, skipping seed")
            return
        
        # Load seed data
        seed_file = 'data/historical_events_seed.json'
        if not os.path.exists(seed_file):
            logger.warning(f"⚠️ Seed file {seed_file} not found, skipping seed")
            return
        
        with open(seed_file, 'r', encoding='utf-8') as f:
            seed_data = json.load(f)
        
        # Add created_at timestamp to each event
        for event in seed_data:
            event['created_at'] = datetime.utcnow()
        
        # Insert seed data
        result = collection.insert_many(seed_data)
        logger.info(f"✅ Seeded {len(result.inserted_ids)} historical events")
        
        # Mark some events as featured
        featured_dates = ["05-29", "07-14", "08-11", "07-31", "08-25"]
        collection.update_many(
            {"date": {"$in": featured_dates}},
            {"$set": {"is_featured": True}}
        )
        logger.info(f"✅ Marked {len(featured_dates)} events as featured")
        
    except Exception as e:
        logger.error(f"❌ Error seeding historical events: {e}")
        raise

def create_ai_content_metadata_collection(db):
    """Create metadata collection for tracking AI content generation"""
    
    collection_name = 'ai_content_metadata'
    
    try:
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
            logger.info(f"✅ Created collection: {collection_name}")
        
        collection = db[collection_name]
        
        # Create indexes
        collection.create_index("content_type")
        collection.create_index("generated_at")
        collection.create_index("status")
        
        # Insert initial metadata
        initial_metadata = {
            "content_type": "historical_events",
            "last_generation": datetime.utcnow(),
            "total_generated": 0,
            "ai_client_version": "1.0.0",
            "status": "active",
            "config": {
                "language": "sl",
                "auto_generation": True,
                "daily_update": True
            }
        }
        
        collection.replace_one(
            {"content_type": "historical_events"},
            initial_metadata,
            upsert=True
        )
        
        logger.info(f"✅ Initialized AI content metadata")
        
        return collection
        
    except Exception as e:
        logger.error(f"❌ Error creating AI metadata collection: {e}")
        raise

def verify_collections(db):
    """Verify that all collections were created successfully"""
    
    required_collections = [
        'historical_events',
        'news_articles', 
        'ai_content_metadata'
    ]
    
    existing_collections = db.list_collection_names()
    
    logger.info("🔍 Verifying collections...")
    
    for collection_name in required_collections:
        if collection_name in existing_collections:
            count = db[collection_name].count_documents({})
            logger.info(f"✅ {collection_name}: {count} documents")
        else:
            logger.error(f"❌ Missing collection: {collection_name}")
            return False
    
    logger.info("✅ All collections verified successfully")
    return True

def show_statistics(db):
    """Show database statistics for AI content features"""
    
    logger.info("📊 Database Statistics:")
    logger.info("=" * 50)
    
    # Historical events stats
    events_collection = db.historical_events
    total_events = events_collection.count_documents({})
    featured_events = events_collection.count_documents({"is_featured": True})
    verified_events = events_collection.count_documents({"is_verified": True})
    ai_generated = events_collection.count_documents({"source": "AI-generated"})
    
    logger.info(f"📅 Historical Events:")
    logger.info(f"   Total: {total_events}")
    logger.info(f"   Featured: {featured_events}")
    logger.info(f"   Verified: {verified_events}")
    logger.info(f"   AI Generated: {ai_generated}")
    
    # News articles stats
    news_collection = db.news_articles
    total_articles = news_collection.count_documents({})
    recent_articles = news_collection.count_documents({
        "published_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0)}
    })
    
    logger.info(f"📰 News Articles:")
    logger.info(f"   Total: {total_articles}")
    logger.info(f"   Today: {recent_articles}")
    
    # Show sample events by category
    categories = events_collection.distinct("category")
    logger.info(f"📂 Event Categories: {', '.join(categories)}")

def main():
    """Main migration function"""
    
    logger.info("🚀 Starting AI Content Features Database Migration")
    logger.info("=" * 60)
    
    # Load environment
    load_env()
    
    try:
        # Connect to database
        db = connect_to_mongodb()
        
        # Create collections
        logger.info("📝 Creating collections...")
        historical_events = create_historical_events_collection(db)
        news_articles = create_news_articles_collection(db)
        ai_metadata = create_ai_content_metadata_collection(db)
        
        # Seed data
        logger.info("🌱 Seeding initial data...")
        seed_historical_events(historical_events)
        
        # Verify setup
        if verify_collections(db):
            logger.info("✅ Migration completed successfully!")
            show_statistics(db)
        else:
            logger.error("❌ Migration verification failed!")
            return 1
        
        logger.info("🎉 AI Content Features database setup complete!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())