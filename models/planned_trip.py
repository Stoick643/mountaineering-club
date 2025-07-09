"""
Planned trip models for organized club trips.
"""
from datetime import datetime
from . import db


class PlannedTrip(db.Model):
    """Model for planned club trips and events."""
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    trip_date = db.Column(db.DateTime, nullable=False)
    difficulty = db.Column(db.String(50))
    max_participants = db.Column(db.Integer)
    meeting_point = db.Column(db.String(200))
    estimated_duration = db.Column(db.String(100))
    price = db.Column(db.Float, default=0)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='open')  # open, full, cancelled, completed
    gear_list = db.Column(db.JSON)  # Store gear items as JSON array
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    participants = db.relationship('TripParticipant', backref='trip', lazy=True, cascade='all, delete-orphan')
    
    @property
    def organizer_name(self):
        """Return the organizer's full name."""
        return self.organizer.full_name if self.organizer else 'Unknown'
    
    @property
    def participant_count(self):
        """Return the number of participants."""
        return len(self.participants)
    
    @property
    def is_full(self):
        """Check if the trip is full."""
        return self.max_participants and len(self.participants) >= self.max_participants
    
    @property
    def is_future(self):
        """Check if the trip is in the future."""
        return self.trip_date > datetime.utcnow()
    
    def __repr__(self):
        return f'<PlannedTrip {self.title}>'


class TripParticipant(db.Model):
    """Model for trip participants and their registration details."""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey('planned_trip.id'), nullable=False)
    phone = db.Column(db.String(20))
    emergency_contact = db.Column(db.String(100))
    notes = db.Column(db.Text)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def user_name(self):
        """Return the participant's full name."""
        return self.user.full_name if self.user else 'Unknown'
    
    def __repr__(self):
        return f'<TripParticipant {self.user_id} -> {self.trip_id}>'