"""
Trip report model for user-generated trip reports.
"""
from datetime import datetime
from . import db


class TripReport(db.Model):
    """Model for user-generated trip reports."""
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200))
    date = db.Column(db.Date)
    difficulty = db.Column(db.String(50))
    images = db.Column(db.JSON)  # Store image URLs as JSON array
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='trip_report', lazy=True, cascade='all, delete-orphan')
    
    @property
    def author_name(self):
        """Return the author's full name."""
        return self.author.full_name if self.author else 'Unknown'
    
    @property
    def photos(self):
        """Return the images list or empty list if None."""
        return self.images or []
    
    def __repr__(self):
        return f'<TripReport {self.title}>'