"""
Database models for the mountaineering club application.
"""
from flask_sqlalchemy import SQLAlchemy

# Database instance - will be initialized by the application
db = SQLAlchemy()

# Import all models to make them available when importing from models
from .user import User
from .announcement import Announcement
from .comment import Comment
from .trip_report import TripReport
from .planned_trip import PlannedTrip, TripParticipant
from .historical_event import HistoricalEvent
from .news import News

__all__ = [
    'db',
    'User',
    'Announcement', 
    'Comment',
    'TripReport',
    'PlannedTrip',
    'TripParticipant',
    'HistoricalEvent',
    'News'
]