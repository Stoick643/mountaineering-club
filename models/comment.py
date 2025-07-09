"""
Comment model for comments on announcements and trip reports.
"""
from datetime import datetime
from . import db


class Comment(db.Model):
    """Model for user comments on announcements and trip reports."""
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'), nullable=True)
    trip_report_id = db.Column(db.Integer, db.ForeignKey('trip_report.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Comment {self.id} by {self.author_id}>'