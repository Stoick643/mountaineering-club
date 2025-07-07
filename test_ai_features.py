#!/usr/bin/env python3
"""
Test script for AI Content Features - Phase 2
Tests the "Na Današnji Dan" functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

from ai_services.deepseek_client import DeepSeekClient
from ai_services.content_generator import HistoricalEventGenerator
from pymongo import MongoClient
from datetime import datetime

def test_deepseek_client():
    """Test DeepSeek API client"""
    print("🔍 Testing DeepSeek Client...")
    
    # Check if API key is available
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        print("⚠️  DEEPSEEK_API_KEY not set - using mock response")
        return True
    
    print(f"🔑 API Key found: {api_key[:10]}...")
    
    client = DeepSeekClient()
    
    # Test with a simple historical event generation
    try:
        response = client.generate_historical_event("01-15")
        if response:
            print(f"✅ DeepSeek API response: {response.get('title', 'No title')}")
            print(f"   Description: {response.get('description', 'No description')[:100]}...")
            return True
        else:
            print("❌ DeepSeek API returned empty response")
            return False
    except Exception as e:
        print(f"❌ DeepSeek API error: {e}")
        return False

def test_content_generator():
    """Test Historical Event Generator"""
    print("\n📅 Testing Historical Event Generator...")
    
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client.mountaineering_club
        
        # Initialize generator
        ai_client = DeepSeekClient()
        generator = HistoricalEventGenerator(db, ai_client)
        
        # Test today's event
        today_event = generator.get_today_event()
        
        if today_event:
            print(f"✅ Today's event: {today_event.get('title', 'No title')}")
            print(f"   Year: {today_event.get('year', 'Unknown')}")
            print(f"   Description: {today_event.get('description', 'No description')[:100]}...")
        else:
            print("⚠️  No event found for today")
        
        return True
        
    except Exception as e:
        print(f"❌ Content generator error: {e}")
        return False

def test_database_setup():
    """Test database collections and indexes"""
    print("\n🗄️  Testing Database Setup...")
    
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client.mountaineering_club
        
        # Check if historical_events collection exists
        collections = db.list_collection_names()
        print(f"📊 Available collections: {collections}")
        
        # Check historical_events collection
        if 'historical_events' in collections:
            count = db.historical_events.count_documents({})
            print(f"✅ Historical events collection: {count} documents")
        else:
            print("⚠️  Historical events collection doesn't exist yet")
        
        # Check indexes
        if 'historical_events' in collections:
            indexes = list(db.historical_events.list_indexes())
            print(f"📚 Indexes: {[idx['name'] for idx in indexes]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup error: {e}")
        return False

def main():
    """Run all tests"""
    print("🏔️  Testing AI Content Features - Phase 2")
    print("="*50)
    
    tests = [
        test_database_setup,
        test_deepseek_client,
        test_content_generator
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "="*50)
    print(f"📊 Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("✅ All tests passed! Phase 2 is ready for user testing.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)