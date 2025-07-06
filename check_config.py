#!/usr/bin/env python3
"""
Production Configuration Checker
Validates that all required environment variables are set correctly.
"""

import os
import sys
import re
from urllib.parse import urlparse

def load_env():
    """Load environment variables from .env file if available"""
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()

def check_required_vars():
    """Check all required environment variables"""
    required_vars = {
        'SECRET_KEY': {
            'required': True,
            'min_length': 32,
            'description': 'Flask secret key for session security'
        },
        'MONGO_URI': {
            'required': True,
            'pattern': r'^mongodb(\+srv)?://',
            'description': 'MongoDB connection string'
        },
        'AWS_ACCESS_KEY_ID': {
            'required': True,
            'min_length': 16,
            'description': 'AWS access key for S3 image storage'
        },
        'AWS_SECRET_ACCESS_KEY': {
            'required': True,
            'min_length': 32,
            'description': 'AWS secret key for S3 image storage'
        },
        'AWS_S3_BUCKET': {
            'required': True,
            'min_length': 3,
            'description': 'AWS S3 bucket name for images'
        }
    }
    
    optional_vars = {
        'GOOGLE_CLIENT_ID': 'Google OAuth client ID',
        'FACEBOOK_CLIENT_ID': 'Facebook OAuth app ID',
        'EMAIL_USER': 'Email service username',
        'OPENWEATHER_API_KEY': 'Weather API key'
    }
    
    print("🔍 Configuration Check Results")
    print("=" * 50)
    
    all_good = True
    
    # Check required variables
    print("\n📋 Required Variables:")
    for var, config in required_vars.items():
        value = os.environ.get(var)
        
        if not value:
            print(f"   ❌ {var}: Missing")
            print(f"      → {config['description']}")
            all_good = False
            continue
        
        # Check minimum length
        if 'min_length' in config and len(value) < config['min_length']:
            print(f"   ⚠️  {var}: Too short (min {config['min_length']} chars)")
            all_good = False
            continue
        
        # Check pattern
        if 'pattern' in config and not re.match(config['pattern'], value):
            print(f"   ⚠️  {var}: Invalid format")
            all_good = False
            continue
        
        # Check for default/placeholder values
        if value in ['dev-secret-key-change-in-production', 'your-aws-access-key', 'your-bucket-name']:
            print(f"   ⚠️  {var}: Using placeholder value")
            all_good = False
            continue
        
        print(f"   ✅ {var}: OK")
    
    # Check optional variables
    print("\n🔧 Optional Variables:")
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value and value not in ['your-google-client-id', 'your-facebook-app-id']:
            print(f"   ✅ {var}: Configured")
        else:
            print(f"   ⚪ {var}: Not configured ({description})")
    
    # Environment-specific checks
    print("\n🌍 Environment Settings:")
    flask_env = os.environ.get('FLASK_ENV', 'development')
    debug = os.environ.get('DEBUG', 'True')
    
    print(f"   FLASK_ENV: {flask_env}")
    print(f"   DEBUG: {debug}")
    
    if flask_env == 'production' and debug.lower() in ['true', '1', 'yes']:
        print("   ⚠️  WARNING: DEBUG is enabled in production!")
        all_good = False
    
    return all_good

def check_database_connection():
    """Test MongoDB connection"""
    print("\n🗄️  Database Connection Test:")
    try:
        from pymongo import MongoClient
        mongo_uri = os.environ.get('MONGO_URI')
        
        if not mongo_uri:
            print("   ❌ MONGO_URI not set")
            return False
        
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        
        # Hide credentials in output
        safe_uri = mongo_uri.split('@')[-1] if '@' in mongo_uri else mongo_uri
        print(f"   ✅ Connected to: {safe_uri}")
        return True
        
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

def main():
    """Main configuration check"""
    print("🏔️  Mountaineering Club - Configuration Validator")
    print("=" * 60)
    
    load_env()
    
    config_ok = check_required_vars()
    db_ok = check_database_connection()
    
    print("\n" + "=" * 60)
    
    if config_ok and db_ok:
        print("🎉 All checks passed! Ready for production deployment.")
        sys.exit(0)
    else:
        print("❌ Configuration issues found. Please fix before deployment.")
        print("\n💡 Tips:")
        print("   - Run 'python generate_secret_key.py' for SECRET_KEY")
        print("   - Set up MongoDB Atlas for MONGO_URI")
        print("   - Configure AWS S3 bucket for image storage")
        sys.exit(1)

if __name__ == "__main__":
    main()