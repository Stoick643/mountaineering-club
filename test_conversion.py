#!/usr/bin/env python3
"""
Test script to verify SQLAlchemy conversion
"""
try:
    from app import app, db, User, Announcement, TripReport, Comment, PlannedTrip, TripParticipant
    
    print("✅ All imports successful")
    
    # Test app context
    with app.app_context():
        # Try to create tables
        db.create_all()
        print("✅ Database tables created successfully")
        
        # Test basic model creation
        print("✅ Models loaded successfully:")
        print(f"  - User: {User}")
        print(f"  - Announcement: {Announcement}")
        print(f"  - TripReport: {TripReport}")
        print(f"  - Comment: {Comment}")
        print(f"  - PlannedTrip: {PlannedTrip}")
        print(f"  - TripParticipant: {TripParticipant}")
        
        print("🎉 SQLAlchemy conversion test passed!")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")