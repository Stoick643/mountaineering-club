#!/usr/bin/env python3
"""
Create an admin user for the mountaineering club app
"""

from app import app, db, User
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_admin():
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@mountaineering.club').first()
        if admin:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin_user = User(
            email='admin@mountaineering.club',
            password_hash=generate_password_hash('admin123'),
            first_name='Admin',
            last_name='User',
            is_approved=True,
            is_admin=True,
            is_email_verified=True,
            created_at=datetime.utcnow()
        )
        
        db.session.add(admin_user)
        db.session.commit()
        
        print("✅ Admin user created successfully!")
        print("Email: admin@mountaineering.club")
        print("Password: admin123")
        print("Please change the password after first login!")

if __name__ == '__main__':
    create_admin()