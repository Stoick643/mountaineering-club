#!/usr/bin/env python3
"""
Seed admin user for production deployment
"""
from app import app, db, User
from werkzeug.security import generate_password_hash

def seed_admin():
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@mountaineering.club').first()
        if admin:
            print('Admin user already exists!')
            return
        
        # Create admin user
        admin = User(
            email='admin@mountaineering.club',
            password_hash=generate_password_hash('admin123'),
            first_name='Admin',
            last_name='User',
            is_admin=True,
            is_approved=True,
            is_email_verified=True
        )
        
        db.session.add(admin)
        db.session.commit()
        print('Admin user created successfully!')

if __name__ == '__main__':
    seed_admin()