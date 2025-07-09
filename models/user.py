"""
User model for authentication and user management.
"""
from datetime import datetime
from . import db


class User(db.Model):
    """User model for authentication and profile management."""
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255))
    last_login = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_picture = db.Column(db.String(255))
    
    # Relationships
    trip_reports = db.relationship('TripReport', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    planned_trips = db.relationship('PlannedTrip', backref='organizer', lazy=True)
    announcements = db.relationship('Announcement', backref='author', lazy=True)
    trip_participations = db.relationship('TripParticipant', backref='user', lazy=True)
    
    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property 
    def password(self):
        """Return password hash for backward compatibility."""
        return self.password_hash
    
    def __repr__(self):
        return f'<User {self.email}>'