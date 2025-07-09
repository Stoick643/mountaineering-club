"""
Test configuration and fixtures for the mountaineering club application.
"""
import pytest
import tempfile
import os
from datetime import datetime
from flask import Flask
from werkzeug.security import generate_password_hash

from models import db, User, Announcement, TripReport, PlannedTrip, News, HistoricalEvent
from ai_services.deepseek_client import DeepSeekClient


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file to serve as the database
    db_fd, db_path = tempfile.mkstemp()
    
    # Create Flask app with testing configuration
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Initialize database with app
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        yield app
        
        # Clean up
        db.session.remove()
        db.drop_all()
    
    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test runner for the Flask application."""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers():
    """Create authorization headers for API testing."""
    return {'Content-Type': 'application/json'}


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        email='test@example.com',
        password_hash=generate_password_hash('password123'),
        first_name='Test',
        last_name='User',
        is_approved=True,
        is_admin=False,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def admin_user():
    """Create a sample admin user for testing."""
    return User(
        email='admin@example.com',
        password_hash=generate_password_hash('admin123'),
        first_name='Admin',
        last_name='User',
        is_approved=True,
        is_admin=True,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_announcement(sample_user):
    """Create a sample announcement for testing."""
    return Announcement(
        title='Test Announcement',
        content='This is a test announcement content.',
        author_id=sample_user.id,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_trip_report(sample_user):
    """Create a sample trip report for testing."""
    return TripReport(
        title='Test Trip Report',
        description='This is a test trip report description.',
        location='Test Mountain',
        date=datetime.utcnow().date(),
        difficulty='Easy',
        author_id=sample_user.id,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_planned_trip(admin_user):
    """Create a sample planned trip for testing."""
    return PlannedTrip(
        title='Test Planned Trip',
        description='This is a test planned trip.',
        location='Test Location',
        trip_date=datetime.utcnow(),
        difficulty='Medium',
        max_participants=10,
        meeting_point='Test Meeting Point',
        organizer_id=admin_user.id,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_news_article():
    """Create a sample news article for testing."""
    return News(
        title='Test News Article',
        summary='This is a test news article summary.',
        original_url='https://example.com/test-article',
        source_name='Test Source',
        relevance_score=7.5,
        language='en',
        category='general',
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_historical_event():
    """Create a sample historical event for testing."""
    return HistoricalEvent(
        date='01-01',
        year=2000,
        title='Test Historical Event',
        description='This is a test historical event.',
        location='Test Location',
        people=['Test Person'],
        category='achievement',
        source='AI-generated',
        language='en',
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_deepseek_client():
    """Create a mock DeepSeek client for testing."""
    class MockDeepSeekClient:
        def __init__(self):
            self.available = True
            
        def is_available(self):
            return self.available
            
        def generate_historical_event(self, date, language='sl'):
            return {
                'date': date,
                'year': 2000,
                'title': 'Mock Event',
                'description': 'Mock description',
                'location': 'Mock Location',
                'people': ['Mock Person'],
                'category': 'achievement',
                'source': 'AI-generated',
                'language': language
            }
            
        def summarize_news_article(self, title, content, language='sl', max_length=150):
            return f"Mock summary of {title}"
            
        def calculate_relevance_score(self, title, content, club_interests=None):
            return 7.5
            
        def translate_content(self, text, target_language='sl'):
            return f"Mock translation: {text}"
    
    return MockDeepSeekClient()


@pytest.fixture
def authenticated_user(client, sample_user):
    """Create an authenticated user session for testing."""
    with client.session_transaction() as sess:
        sess['user_id'] = sample_user.id
        sess['user_name'] = sample_user.full_name
        sess['is_admin'] = sample_user.is_admin
    return sample_user


@pytest.fixture
def authenticated_admin(client, admin_user):
    """Create an authenticated admin session for testing."""
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user.id
        sess['user_name'] = admin_user.full_name
        sess['is_admin'] = admin_user.is_admin
    return admin_user