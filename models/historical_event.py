"""
Historical event model for AI-generated mountaineering history.
"""
from datetime import datetime
from . import db


class HistoricalEvent(db.Model):
    """Model for historical mountaineering events."""
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(5), nullable=False)  # MM-DD format
    year = db.Column(db.Integer)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200))
    people = db.Column(db.JSON)  # Store people names as JSON array
    category = db.Column(db.String(50))  # first_ascent, tragedy, discovery, etc.
    reference_url = db.Column(db.String(500))  # Optional reference link
    source = db.Column(db.String(50), default='AI-generated')
    language = db.Column(db.String(5), default='sl')
    is_featured = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert the historical event to a dictionary."""
        return {
            'id': self.id,
            'date': self.date,
            'year': self.year,
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'people': self.people or [],
            'category': self.category,
            'reference_url': self.reference_url,
            'source': self.source,
            'language': self.language,
            'is_featured': self.is_featured,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at and hasattr(self.created_at, 'isoformat') else str(self.created_at) if self.created_at else None
        }
    
    def __repr__(self):
        return f'<HistoricalEvent {self.date}: {self.title}>'