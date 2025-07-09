"""
Unit tests for database models.
"""
import pytest
from datetime import datetime, date
from werkzeug.security import generate_password_hash

from models import db, User, Announcement, TripReport, PlannedTrip, TripParticipant, News, HistoricalEvent, Comment


@pytest.mark.unit
class TestUser:
    """Test cases for the User model."""
    
    def test_user_creation(self, app, sample_user):
        """Test basic user creation."""
        with app.app_context():
            db.session.add(sample_user)
            db.session.commit()
            
            assert sample_user.id is not None
            assert sample_user.email == 'test@example.com'
            assert sample_user.full_name == 'Test User'
            assert sample_user.is_approved is True
            assert sample_user.is_admin is False
    
    def test_user_full_name_property(self, sample_user):
        """Test the full_name property."""
        assert sample_user.full_name == 'Test User'
        
        # Test with empty last name
        sample_user.last_name = ''
        assert sample_user.full_name == 'Test'
        
        # Test with empty first name
        sample_user.first_name = ''
        assert sample_user.full_name == ''
    
    def test_user_password_property(self, sample_user):
        """Test the password property returns hash."""
        assert sample_user.password == sample_user.password_hash
    
    def test_user_relationships(self, app, sample_user):
        """Test user relationships with other models."""
        with app.app_context():
            db.session.add(sample_user)
            db.session.commit()
            
            # Test announcements relationship
            announcement = Announcement(
                title='Test',
                content='Test content',
                author_id=sample_user.id
            )
            db.session.add(announcement)
            db.session.commit()
            
            assert len(sample_user.announcements) == 1
            assert sample_user.announcements[0].title == 'Test'


@pytest.mark.unit
class TestAnnouncement:
    """Test cases for the Announcement model."""
    
    def test_announcement_creation(self, app, sample_user):
        """Test basic announcement creation."""
        with app.app_context():
            db.session.add(sample_user)
            db.session.commit()
            
            announcement = Announcement(
                title='Test Announcement',
                content='Test content',
                author_id=sample_user.id
            )
            db.session.add(announcement)
            db.session.commit()
            
            assert announcement.id is not None
            assert announcement.title == 'Test Announcement'
            assert announcement.content == 'Test content'
            assert announcement.author_id == sample_user.id
    
    def test_announcement_author_name_property(self, app, sample_user):
        """Test the author_name property."""
        with app.app_context():
            db.session.add(sample_user)
            db.session.commit()
            
            announcement = Announcement(
                title='Test',
                content='Test content',
                author_id=sample_user.id
            )
            db.session.add(announcement)
            db.session.commit()
            
            assert announcement.author_name == 'Test User'


@pytest.mark.unit
class TestTripReport:
    """Test cases for the TripReport model."""
    
    def test_trip_report_creation(self, app, sample_user):
        """Test basic trip report creation."""
        with app.app_context():
            db.session.add(sample_user)
            db.session.commit()
            
            trip_report = TripReport(
                title='Test Trip',
                description='Test description',
                location='Test Mountain',
                date=date.today(),
                difficulty='Easy',
                author_id=sample_user.id
            )
            db.session.add(trip_report)
            db.session.commit()
            
            assert trip_report.id is not None
            assert trip_report.title == 'Test Trip'
            assert trip_report.location == 'Test Mountain'
            assert trip_report.difficulty == 'Easy'
    
    def test_trip_report_photos_property(self, app, sample_user):
        """Test the photos property."""
        with app.app_context():
            db.session.add(sample_user)
            db.session.commit()
            
            # Test with no images
            trip_report = TripReport(
                title='Test Trip',
                description='Test description',
                author_id=sample_user.id
            )
            db.session.add(trip_report)
            db.session.commit()
            
            assert trip_report.photos == []
            
            # Test with images
            trip_report.images = [{'url': 'test.jpg'}]
            assert trip_report.photos == [{'url': 'test.jpg'}]


@pytest.mark.unit
class TestPlannedTrip:
    """Test cases for the PlannedTrip model."""
    
    def test_planned_trip_creation(self, app, admin_user):
        """Test basic planned trip creation."""
        with app.app_context():
            db.session.add(admin_user)
            db.session.commit()
            
            planned_trip = PlannedTrip(
                title='Test Planned Trip',
                description='Test description',
                location='Test Location',
                trip_date=datetime.utcnow(),
                organizer_id=admin_user.id
            )
            db.session.add(planned_trip)
            db.session.commit()
            
            assert planned_trip.id is not None
            assert planned_trip.title == 'Test Planned Trip'
            assert planned_trip.organizer_id == admin_user.id
    
    def test_planned_trip_properties(self, app, admin_user, sample_user):
        """Test planned trip properties."""
        with app.app_context():
            db.session.add(admin_user)
            db.session.add(sample_user)
            db.session.commit()
            
            planned_trip = PlannedTrip(
                title='Test Trip',
                description='Test description',
                location='Test Location',
                trip_date=datetime.utcnow(),
                max_participants=2,
                organizer_id=admin_user.id
            )
            db.session.add(planned_trip)
            db.session.commit()
            
            # Test initial state
            assert planned_trip.participant_count == 0
            assert planned_trip.is_full is False
            assert planned_trip.organizer_name == 'Admin User'
            
            # Add participant
            participant = TripParticipant(
                user_id=sample_user.id,
                trip_id=planned_trip.id
            )
            db.session.add(participant)
            db.session.commit()
            
            assert planned_trip.participant_count == 1
            assert planned_trip.is_full is False
            
            # Add second participant to fill trip
            participant2 = TripParticipant(
                user_id=admin_user.id,
                trip_id=planned_trip.id
            )
            db.session.add(participant2)
            db.session.commit()
            
            assert planned_trip.participant_count == 2
            assert planned_trip.is_full is True


@pytest.mark.unit
class TestNews:
    """Test cases for the News model."""
    
    def test_news_creation(self, app):
        """Test basic news creation."""
        with app.app_context():
            news = News(
                title='Test News',
                summary='Test summary',
                original_url='https://example.com',
                source_name='Test Source',
                relevance_score=8.0,
                language='en',
                category='general'
            )
            db.session.add(news)
            db.session.commit()
            
            assert news.id is not None
            assert news.title == 'Test News'
            assert news.relevance_score == 8.0
            assert news.language == 'en'
    
    def test_news_to_dict(self, app):
        """Test news to_dict method."""
        with app.app_context():
            news = News(
                title='Test News',
                summary='Test summary',
                original_url='https://example.com',
                source_name='Test Source',
                relevance_score=8.0,
                language='en',
                category='general'
            )
            db.session.add(news)
            db.session.commit()
            
            news_dict = news.to_dict()
            assert news_dict['title'] == 'Test News'
            assert news_dict['relevance_score'] == 8.0
            assert news_dict['language'] == 'en'
            assert 'created_at' in news_dict


@pytest.mark.unit
class TestHistoricalEvent:
    """Test cases for the HistoricalEvent model."""
    
    def test_historical_event_creation(self, app):
        """Test basic historical event creation."""
        with app.app_context():
            event = HistoricalEvent(
                date='01-01',
                year=2000,
                title='Test Event',
                description='Test description',
                location='Test Location',
                people=['Test Person'],
                category='achievement'
            )
            db.session.add(event)
            db.session.commit()
            
            assert event.id is not None
            assert event.date == '01-01'
            assert event.year == 2000
            assert event.title == 'Test Event'
            assert event.people == ['Test Person']
    
    def test_historical_event_to_dict(self, app):
        """Test historical event to_dict method."""
        with app.app_context():
            event = HistoricalEvent(
                date='01-01',
                year=2000,
                title='Test Event',
                description='Test description',
                location='Test Location',
                people=['Test Person'],
                category='achievement'
            )
            db.session.add(event)
            db.session.commit()
            
            event_dict = event.to_dict()
            assert event_dict['date'] == '01-01'
            assert event_dict['year'] == 2000
            assert event_dict['title'] == 'Test Event'
            assert event_dict['people'] == ['Test Person']
            assert 'created_at' in event_dict