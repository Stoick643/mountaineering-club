"""
Main application file for the mountaineering club.
Refactored to use service layer and organized route modules.
"""
from flask import Flask
from flask_migrate import Migrate
from flask_socketio import SocketIO
from authlib.integrations.flask_client import OAuth
import os
import logging
import threading
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models and services
from models import db
from services.news_service import NewsService

# Import route blueprints
from routes.main import main_bp
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.api import api_bp
from routes.trips import trips_bp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    """Application factory pattern."""
    app = Flask(__name__)
    
    # Basic Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///mountaineering_club.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
    
    # Production Security Settings
    if os.environ.get('FLASK_ENV') == 'production':
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            PERMANENT_SESSION_LIFETIME=int(os.environ.get('PERMANENT_SESSION_LIFETIME', 3600)),
            WTF_CSRF_TIME_LIMIT=None,
            SEND_FILE_MAX_AGE_DEFAULT=31536000,  # 1 year cache for static files
        )
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Initialize OAuth
    oauth = OAuth(app)
    
    # Configure Google OAuth
    oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    
    # Configure Facebook OAuth
    oauth.register(
        name='facebook',
        client_id=os.environ.get('FACEBOOK_APP_ID'),
        client_secret=os.environ.get('FACEBOOK_APP_SECRET'),
        api_base_url='https://graph.facebook.com/',
        access_token_url='https://graph.facebook.com/oauth/access_token',
        authorize_url='https://www.facebook.com/dialog/oauth',
        client_kwargs={'scope': 'email'},
    )
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(trips_bp)
    
    return app, socketio


def news_update_scheduler():
    """Background task to update news every 24 hours at 6 AM."""
    while True:
        try:
            # Calculate seconds until next 6 AM
            now = datetime.now()
            next_6am = now.replace(hour=6, minute=0, second=0, microsecond=0)
            
            # If it's already past 6 AM today, schedule for tomorrow
            if now.hour >= 6:
                next_6am = next_6am + timedelta(days=1)
            
            sleep_seconds = (next_6am - now).total_seconds()
            
            logger.info(f"News update scheduled for {next_6am}, sleeping for {sleep_seconds/3600:.1f} hours")
            time.sleep(sleep_seconds)
            
            # Update news
            with app.app_context():
                try:
                    news_service = NewsService()
                    success, message, stats = news_service.update_news_feed()
                    logger.info(f"Scheduled news update completed: {stats}")
                except Exception as e:
                    logger.error(f"Scheduled news update failed: {e}")
            
        except Exception as e:
            logger.error(f"News scheduler error: {e}")
            # Sleep for 1 hour before retrying
            time.sleep(3600)


def start_background_tasks():
    """Start background tasks."""
    # Run scheduler in both development and production for testing
    # In production, consider using a proper job scheduler like Celery
    news_thread = threading.Thread(target=news_update_scheduler, daemon=True)
    news_thread.start()
    logger.info("Background news scheduler started")


# Create application instance
app, socketio = create_app()

if __name__ == '__main__':
    # Start background tasks
    start_background_tasks()
    
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=True, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)