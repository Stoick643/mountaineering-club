"""
News model for curated mountaineering news articles.
"""
from datetime import datetime
from . import db


class News(db.Model):
    """Model for curated mountaineering news articles."""
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    summary = db.Column(db.Text)
    original_url = db.Column(db.String(500))
    source_name = db.Column(db.String(100))
    relevance_score = db.Column(db.Float, default=5.0)
    language = db.Column(db.String(5), default='sl')
    category = db.Column(db.String(50))  # safety, equipment, achievement, etc.
    is_featured = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert the news article to a dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'original_url': self.original_url,
            'source_name': self.source_name,
            'relevance_score': self.relevance_score,
            'language': self.language,
            'category': self.category,
            'is_featured': self.is_featured,
            'published_at': self.published_at.isoformat() if self.published_at and hasattr(self.published_at, 'isoformat') else str(self.published_at) if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at and hasattr(self.created_at, 'isoformat') else str(self.created_at) if self.created_at else None
        }
    
    def __repr__(self):
        return f'<News {self.title}>'