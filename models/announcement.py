"""
Announcement model for club announcements and news.
"""
from datetime import datetime
from . import db


class Announcement(db.Model):
    """Model for club announcements and news posts."""
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='announcement', lazy=True, cascade='all, delete-orphan')
    
    @property
    def author_name(self):
        """Return the author's full name."""
        return self.author.full_name if self.author else 'Unknown'
    
    def __repr__(self):
        return f'<Announcement {self.title}>'