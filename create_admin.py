#!/usr/bin/env python3
"""
Admin User Creation Script for Mountaineering Club
Creates the first admin user for the application.
"""

import os
import sys
from getpass import getpass
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime
import re

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, "Password is valid"

def connect_to_mongodb():
    """Connect to MongoDB using environment variables"""
    try:
        # Try to load from .env file if available
        if os.path.exists('.env'):
            from dotenv import load_dotenv
            load_dotenv()
        
        mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/mountaineering_club')
        client = MongoClient(mongo_uri)
        
        # Test connection
        client.admin.command('ping')
        db = client.get_database()
        
        print(f"✅ Connected to MongoDB: {mongo_uri.split('@')[-1] if '@' in mongo_uri else mongo_uri}")
        return db
    
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        print("\n💡 Make sure:")
        print("   - MongoDB is running")
        print("   - MONGO_URI is set correctly in .env file")
        print("   - Network connectivity is available")
        sys.exit(1)

def check_existing_admins(db):
    """Check if any admin users already exist"""
    admin_count = db.users.count_documents({'is_admin': True})
    if admin_count > 0:
        print(f"⚠️  Found {admin_count} existing admin user(s)")
        response = input("Do you want to create another admin? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Admin creation cancelled.")
            sys.exit(0)

def create_admin_user(db):
    """Interactive admin user creation"""
    print("\n🔧 Creating Admin User for Mountaineering Club")
    print("=" * 50)
    
    # Get admin details
    while True:
        email = input("Admin email: ").strip()
        if not email:
            print("❌ Email cannot be empty")
            continue
        if not validate_email(email):
            print("❌ Invalid email format")
            continue
        
        # Check if email already exists
        if db.users.find_one({'email': email}):
            print("❌ User with this email already exists")
            continue
        break
    
    while True:
        full_name = input("Admin full name: ").strip()
        if not full_name:
            print("❌ Name cannot be empty")
            continue
        if len(full_name) < 2:
            print("❌ Name must be at least 2 characters")
            continue
        break
    
    while True:
        password = getpass("Admin password (hidden): ").strip()
        if not password:
            print("❌ Password cannot be empty")
            continue
        
        is_valid, message = validate_password(password)
        if not is_valid:
            print(f"❌ {message}")
            continue
        
        password_confirm = getpass("Confirm password (hidden): ").strip()
        if password != password_confirm:
            print("❌ Passwords do not match")
            continue
        break
    
    # Create admin user
    admin_data = {
        'email': email,
        'full_name': full_name,
        'password': generate_password_hash(password),
        'is_admin': True,
        'is_approved': True,
        'created_at': datetime.utcnow(),
        'profile_picture': None,
        'oauth_provider': None
    }
    
    try:
        result = db.users.insert_one(admin_data)
        print(f"\n✅ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Name: {full_name}")
        print(f"   User ID: {result.inserted_id}")
        print(f"\n🎯 You can now login at: http://localhost:5000/login")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        sys.exit(1)

def main():
    """Main function"""
    print("🏔️  Mountaineering Club - Admin Creation Tool")
    print("=" * 50)
    
    # Connect to database
    db = connect_to_mongodb()
    
    # Check existing admins
    check_existing_admins(db)
    
    # Create admin user
    create_admin_user(db)
    
    print("\n🎉 Admin creation completed!")
    print("💡 Tip: You can run this script again to create additional admins")

if __name__ == "__main__":
    main()