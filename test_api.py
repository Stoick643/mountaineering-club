#!/usr/bin/env python3
"""
Test the API endpoints directly
"""

import requests
import json
from datetime import datetime

def test_today_in_history():
    """Test the today-in-history API endpoint"""
    print("🔍 Testing /api/today-in-history endpoint...")
    
    try:
        response = requests.get('http://localhost:5000/api/today-in-history', timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Response: {json.dumps(data, indent=2)}")
            
            if data.get('success') and data.get('event'):
                event = data['event']
                print(f"📅 Event Title: {event.get('title', 'No title')}")
                print(f"📅 Event Year: {event.get('year', 'Unknown')}")
                print(f"📅 Event Description: {event.get('description', 'No description')[:100]}...")
                return True
            else:
                print("⚠️  No event data in response")
                return False
        else:
            print(f"❌ API returned status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_history_random():
    """Test the random history API endpoint"""
    print("\n🎲 Testing /api/history/random endpoint...")
    
    try:
        response = requests.get('http://localhost:5000/api/history/random', timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ API returned status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Run API tests"""
    print("🏔️  Testing AI Content Features API Endpoints")
    print("="*50)
    
    # Test endpoints
    today_result = test_today_in_history()
    random_result = test_history_random()
    
    print("\n" + "="*50)
    print(f"📊 Test Results: {sum([today_result, random_result])}/2 passed")
    
    if today_result and random_result:
        print("✅ All API endpoints are working!")
    else:
        print("⚠️  Some API endpoints failed.")
    
    return today_result and random_result

if __name__ == "__main__":
    success = main()