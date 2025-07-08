#!/usr/bin/env python3
"""
Complete deployment setup: migrations + admin seeding
"""
import subprocess
import sys
from app import app, db, User
from werkzeug.security import generate_password_hash

def run_migrations():
    """Run database migrations"""
    try:
        result = subprocess.run(['flask', 'db', 'upgrade'], check=True, capture_output=True, text=True)
        print("✅ Database migrations completed")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        print(e.stderr)
        sys.exit(1)

def seed_admin():
    """Create admin user"""
    with app.app_context():
        admin = User.query.filter_by(email='admin@mountaineering.club').first()
        if admin:
            print('✅ Admin user already exists')
            return
        
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
        print('✅ Admin user created successfully')

if __name__ == '__main__':
    run_migrations()
    seed_admin()
    print('🚀 Deployment setup complete!')