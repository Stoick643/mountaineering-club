#!/usr/bin/env python3
"""
Simple script to run the Flask app with environment variables loaded
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import and run the app
from app import app

if __name__ == "__main__":
    print("🏔️  Starting Mountaineering Club Platform...")
    print(f"📍 Running on port 5000")
    print(f"🔑 DeepSeek API Key: {'✅ Set' if os.getenv('DEEPSEEK_API_KEY') else '❌ Not set'}")
    print(f"🗄️  MongoDB URI: {os.getenv('MONGO_URI', 'mongodb://localhost:27017/mountaineering_club')}")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"❌ Failed to start app: {e}")