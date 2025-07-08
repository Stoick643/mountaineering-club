from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import logging
from functools import wraps
import redis
from image_handler import ImageHandler
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit, join_room, leave_room
from authlib.integrations.flask_client import OAuth
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json

# Import AI services
from ai_services.content_generator_sqlalchemy import HistoricalEventGenerator
from ai_services.deepseek_client import DeepSeekClient
from ai_services.news_curator import NewsCurator

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
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255))
    last_login = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_picture = db.Column(db.String(255))
    
    # Relationships
    trip_reports = db.relationship('TripReport', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    planned_trips = db.relationship('PlannedTrip', backref='organizer', lazy=True)
    # chat_messages relationship removed - feature cancelled
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property 
    def password(self):
        return self.password_hash

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = db.relationship('User', backref='announcements')
    comments = db.relationship('Comment', backref='announcement', lazy=True, cascade='all, delete-orphan')
    
    @property
    def author_name(self):
        return self.author.full_name if self.author else 'Unknown'

class TripReport(db.Model):
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
        return self.author.full_name if self.author else 'Unknown'
    
    @property
    def photos(self):
        return self.images or []

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'), nullable=True)
    trip_report_id = db.Column(db.Integer, db.ForeignKey('trip_report.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PlannedTrip(db.Model):
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
        return self.organizer.full_name if self.organizer else 'Unknown'
    
    @property
    def participant_count(self):
        return len(self.participants)
    
    @property
    def is_full(self):
        return self.max_participants and len(self.participants) >= self.max_participants
    
    @property
    def is_future(self):
        return self.trip_date > datetime.utcnow()

class TripParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey('planned_trip.id'), nullable=False)
    phone = db.Column(db.String(20))
    emergency_contact = db.Column(db.String(100))
    notes = db.Column(db.Text)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='trip_participations')
    
    @property
    def user_name(self):
        return self.user.full_name if self.user else 'Unknown'

class HistoricalEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(5), nullable=False)  # MM-DD format
    year = db.Column(db.Integer)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200))
    people = db.Column(db.JSON)  # Store people names as JSON array
    category = db.Column(db.String(50))  # first_ascent, tragedy, discovery, etc.
    source = db.Column(db.String(50), default='AI-generated')
    language = db.Column(db.String(5), default='sl')
    is_featured = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'year': self.year,
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'people': self.people or [],
            'category': self.category,
            'source': self.source,
            'language': self.language,
            'is_featured': self.is_featured,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class News(db.Model):
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
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ChatMessage model removed - feature cancelled
# Disable Redis for now - networking issue
# redis_client = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'), 
#                           port=int(os.environ.get('REDIS_PORT', 6379)), 
#                           db=0, decode_responses=True)
# limiter = Limiter(
#     key_func=get_remote_address,
#     app=app,
#     default_limits=["200 per day", "50 per hour"],
#     storage_uri=f"redis://{os.environ.get('REDIS_HOST', 'localhost')}:{os.environ.get('REDIS_PORT', 6379)}"
# )
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize image handler
image_handler = ImageHandler()

# Initialize AI services
deepseek_client = DeepSeekClient()

# Initialize AI service generators (will be set up after app context)
def get_historical_generator():
    return HistoricalEventGenerator(db, HistoricalEvent, deepseek_client)

def get_news_curator():
    return NewsCurator(db, News, deepseek_client)

# Initialize OAuth
oauth = OAuth(app)

# Configure Google OAuth
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Configure Facebook OAuth
facebook = oauth.register(
    name='facebook',
    client_id=os.environ.get('FACEBOOK_APP_ID'),
    client_secret=os.environ.get('FACEBOOK_APP_SECRET'),
    api_base_url='https://graph.facebook.com/',
    access_token_url='https://graph.facebook.com/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    client_kwargs={'scope': 'email'},
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Health check route for deployment platforms
@app.route('/health')
def health_check():
    """Health check endpoint for Railway, DigitalOcean, etc."""
    try:
        # Test database connection
        User.query.count()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

# Routes
@app.route('/')
def home():
    # Get recent announcements for homepage
    try:
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all()
    except Exception as e:
        logger.error(f"Database error: {e}")
        announcements = []
    return render_template('home.html', announcements=announcements)

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
    recent_trips = TripReport.query.order_by(TripReport.created_at.desc()).limit(5).all()
    return render_template('dashboard.html', user=user, announcements=announcements, recent_trips=recent_trips)

@app.route('/register', methods=['GET', 'POST'])
# @limiter.limit("5 per minute")  # Disabled with Redis
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Split full name into first and last name
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Create new user (pending approval)
        new_user = User(
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            is_approved=False,
            is_admin=False,
            created_at=datetime.utcnow(),
            profile_picture=None
        )
        
        db.session.add(new_user)
        db.session.commit()
        logger.info(f"New user registered: {email}")
        
        flash('Registration successful! Please wait for admin approval.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
# @limiter.limit("10 per minute")  # Disabled with Redis
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.is_approved:
                flash('Account pending approval', 'warning')
                return render_template('login.html')
            
            session['user_id'] = user.id
            session['user_name'] = user.full_name
            session['is_admin'] = user.is_admin
            
            logger.info(f"User logged in: {email}")
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Uspešno ste se odjavili', 'success')
    return redirect(url_for('home'))

# OAuth routes
@app.route('/auth/<provider>')
def oauth_login(provider):
    if provider == 'google':
        redirect_uri = url_for('oauth_callback', provider='google', _external=True)
        return google.authorize_redirect(redirect_uri)
    elif provider == 'facebook':
        redirect_uri = url_for('oauth_callback', provider='facebook', _external=True)
        return facebook.authorize_redirect(redirect_uri)
    else:
        flash('Nepodprt ponudnik prijave', 'error')
        return redirect(url_for('login'))

@app.route('/auth/<provider>/callback')
def oauth_callback(provider):
    try:
        if provider == 'google':
            token = google.authorize_access_token()
            user_info = token.get('userinfo')
            if user_info:
                email = user_info['email']
                full_name = user_info['name']
                profile_picture = user_info.get('picture')
        
        elif provider == 'facebook':
            token = facebook.authorize_access_token()
            resp = facebook.get('me?fields=id,name,email,picture', token=token)
            user_info = resp.json()
            email = user_info.get('email')
            full_name = user_info.get('name')
            profile_picture = user_info.get('picture', {}).get('data', {}).get('url')
            
        else:
            flash('Nepodprt ponudnik prijave', 'error')
            return redirect(url_for('login'))
        
        if not email:
            flash('Ni bilo mogoče pridobiti e-poštnega naslova', 'error')
            return redirect(url_for('login'))
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if user:
            # User exists - log them in
            if not user.is_approved:
                flash('Vaš račun še čaka na odobritev skrbnika', 'warning')
                return redirect(url_for('login'))
            
            # Update profile picture if available
            if profile_picture and not user.profile_picture:
                user.profile_picture = profile_picture
                db.session.commit()
            
            # Log user in
            session['user_id'] = user.id
            session['user_name'] = user.full_name
            session['is_admin'] = user.is_admin
            
            logger.info(f"User logged in via {provider}: {email}")
            flash(f'Uspešno ste se prijavili preko {provider.title()}', 'success')
            return redirect(url_for('dashboard'))
        
        else:
            # Create new user account (pending approval)
            # Split full name into first and last name
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            new_user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                password_hash='',  # OAuth users don't have passwords
                profile_picture=profile_picture,
                is_approved=False,
                is_admin=False,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_user)
            db.session.commit()
            logger.info(f"New OAuth user registered via {provider}: {email}")
            
            flash(f'Račun ustvarjen preko {provider.title()}! Prosimo, počakajte na odobritev skrbnika.', 'success')
            return redirect(url_for('login'))
    
    except Exception as e:
        logger.error(f"OAuth {provider} error: {e}")
        db.session.rollback()
        flash('Napaka pri prijavi. Poskusite znova.', 'error')
        return redirect(url_for('login'))

# Admin routes
@app.route('/admin')
@admin_required
def admin_panel():
    pending_users = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).all()
    all_users = User.query.order_by(User.created_at.desc()).all()
    stats = {
        'total_users': User.query.count(),
        'pending_approval': User.query.filter_by(is_approved=False).count(),
        'approved_users': User.query.filter_by(is_approved=True).count(),
        'admin_users': User.query.filter_by(is_admin=True).count()
    }
    return render_template('admin_panel.html', 
                         pending_users=pending_users, 
                         all_users=all_users, 
                         stats=stats)

@app.route('/admin/approve_user/<user_id>')
@admin_required
def approve_user(user_id):
    try:
        user = User.query.get(int(user_id))
        if user:
            user.is_approved = True
            db.session.commit()
            flash(f'User {user.full_name} approved successfully', 'success')
            logger.info(f"Admin {session['user_name']} approved user {user.email}")
        else:
            flash('User not found', 'error')
    except Exception as e:
        flash('Error approving user', 'error')
        logger.error(f"Error approving user {user_id}: {e}")
        db.session.rollback()
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject_user/<int:user_id>')
@admin_required
def reject_user(user_id):
    try:
        user = User.query.get(user_id)
        if user:
            user_name = user.full_name
            user_email = user.email
            db.session.delete(user)
            db.session.commit()
            flash(f'User {user_name} rejected and removed', 'warning')
            logger.info(f"Admin {session['user_name']} rejected user {user_email}")
        else:
            flash('User not found', 'error')
    except Exception as e:
        flash('Error rejecting user', 'error')
        logger.error(f"Error rejecting user {user_id}: {e}")
        db.session.rollback()
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/toggle_admin/<int:user_id>')
@admin_required
def toggle_admin(user_id):
    try:
        user = User.query.get(user_id)
        if user:
            new_admin_status = not user.is_admin
            user.is_admin = new_admin_status
            db.session.commit()
            action = 'promoted to' if new_admin_status else 'removed from'
            flash(f'{user.full_name} {action} admin', 'success')
            logger.info(f"Admin {session['user_name']} changed admin status for {user.email}")
        else:
            flash('User not found', 'error')
    except Exception as e:
        flash('Error updating admin status', 'error')
        logger.error(f"Error toggling admin for {user_id}: {e}")
        db.session.rollback()
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/announcements')
@admin_required
def admin_announcements():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('admin_announcements.html', announcements=announcements)

@app.route('/admin/announcements/create', methods=['GET', 'POST'])
@admin_required
def create_announcement():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if title and content:
            new_announcement = Announcement(
                title=title,
                content=content,
                author_id=session['user_id'],
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_announcement)
            db.session.commit()
            flash('Announcement created successfully', 'success')
            logger.info(f"Admin {session['user_name']} created announcement: {title}")
            return redirect(url_for('admin_announcements'))
        else:
            flash('Title and content are required', 'error')
    
    return render_template('create_announcement.html')

@app.route('/admin/announcements/delete/<int:announcement_id>')
@admin_required
def delete_announcement(announcement_id):
    try:
        announcement = Announcement.query.get(announcement_id)
        if announcement:
            db.session.delete(announcement)
            db.session.commit()
            flash('Announcement deleted successfully', 'success')
            logger.info(f"Admin {session['user_name']} deleted announcement: {announcement.title}")
        else:
            flash('Announcement not found', 'error')
    except Exception as e:
        flash('Error deleting announcement', 'error')
        logger.error(f"Error deleting announcement {announcement_id}: {e}")
        db.session.rollback()
    
    return redirect(url_for('admin_announcements'))

# Comments routes
@app.route('/api/comments/<content_type>/<content_id>')
@login_required
def get_comments(content_type, content_id):
    """Get comments for announcements or trip reports"""
    try:
        if content_type not in ['announcement', 'trip_report']:
            return jsonify({'error': 'Invalid content type'}), 400
        
        # Get comments based on content type
        if content_type == 'announcement':
            comments = Comment.query.filter_by(announcement_id=int(content_id)).order_by(Comment.created_at.asc()).all()
        else:  # trip_report
            comments = Comment.query.filter_by(trip_report_id=int(content_id)).order_by(Comment.created_at.asc()).all()
        
        # Convert to JSON format
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'content': comment.content,
                'author_name': comment.author.full_name if comment.author else 'Unknown',
                'author_id': comment.author_id,
                'created_at': comment.created_at.isoformat()
            })
        
        return jsonify({'comments': comments_data})
    
    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        return jsonify({'error': 'Error fetching comments'}), 500

@app.route('/api/comments/<content_type>/<content_id>', methods=['POST'])
@login_required
def add_comment(content_type, content_id):
    """Add a comment to announcements or trip reports"""
    try:
        if content_type not in ['announcement', 'trip_report']:
            return jsonify({'error': 'Invalid content type'}), 400
        
        data = request.get_json()
        comment_text = data.get('comment', '').strip()
        
        if not comment_text:
            return jsonify({'error': 'Comment cannot be empty'}), 400
        
        if len(comment_text) > 1000:
            return jsonify({'error': 'Comment too long (max 1000 characters)'}), 400
        
        # Verify the content exists
        if content_type == 'announcement':
            content = Announcement.query.get(int(content_id))
        else:  # trip_report
            content = TripReport.query.get(int(content_id))
        
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        # Create new comment
        new_comment = Comment(
            content=comment_text,
            author_id=session['user_id'],
            announcement_id=int(content_id) if content_type == 'announcement' else None,
            trip_report_id=int(content_id) if content_type == 'trip_report' else None,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_comment)
        db.session.commit()
        
        # Return the new comment data
        comment_data = {
            'id': new_comment.id,
            'content': new_comment.content,
            'author_name': new_comment.author.full_name,
            'author_id': new_comment.author_id,
            'created_at': new_comment.created_at.isoformat()
        }
        
        logger.info(f"User {session['user_name']} added comment to {content_type} {content_id}")
        
        return jsonify({'comment': comment_data}), 201
    
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        db.session.rollback()
        return jsonify({'error': 'Error adding comment'}), 500

@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Delete a comment (only by author or admin)"""
    try:
        comment = Comment.query.get(comment_id)
        
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        # Check if user can delete this comment
        if comment.author_id != session['user_id'] and not session.get('is_admin', False):
            return jsonify({'error': 'Not authorized to delete this comment'}), 403
        
        db.session.delete(comment)
        db.session.commit()
        
        logger.info(f"User {session['user_name']} deleted comment {comment_id}")
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Error deleting comment: {e}")
        db.session.rollback()
        return jsonify({'error': 'Error deleting comment'}), 500

# AI Content Features Routes
@app.route('/api/today-in-history')
@login_required
def today_in_history():
    """Get historical event for today"""
    try:
        # Import AI services
        from ai_services.content_generator_sqlalchemy import HistoricalEventGenerator
        from ai_services.deepseek_client import DeepSeekClient
        
        # Initialize services
        ai_client = DeepSeekClient()
        event_generator = HistoricalEventGenerator(db, HistoricalEvent, ai_client)
        
        # Get today's event
        today_event = event_generator.get_today_event()
        
        if today_event:
            # Convert ObjectId to string for JSON serialization
            if '_id' in today_event:
                today_event['_id'] = str(today_event['_id'])
            if 'created_at' in today_event:
                today_event['created_at'] = today_event['created_at'].isoformat()
            
            return jsonify({
                'success': True,
                'event': today_event
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ni dogodka za današnji dan'
            }), 404
            
    except Exception as e:
        logger.error(f"Error fetching today's historical event: {e}")
        return jsonify({
            'success': False,
            'error': 'Napaka pri pridobivanju dogodka'
        }), 500

@app.route('/api/history/<date>')
@login_required  
def history_by_date(date):
    """Get historical event for specific date (MM-DD format)"""
    try:
        # Validate date format
        import re
        if not re.match(r'^\d{2}-\d{2}$', date):
            return jsonify({
                'success': False,
                'error': 'Neveljaven format datuma (uporabite MM-DD)'
            }), 400
        
        # Import AI services
        from ai_services.content_generator_sqlalchemy import HistoricalEventGenerator
        from ai_services.deepseek_client import DeepSeekClient
        
        # Initialize services
        ai_client = DeepSeekClient()
        event_generator = HistoricalEventGenerator(db, HistoricalEvent, ai_client)
        
        # Get event for specific date
        event = event_generator.get_today_event(date)
        
        if event:
            # Convert ObjectId to string for JSON serialization
            if '_id' in event:
                event['_id'] = str(event['_id'])
            if 'created_at' in event:
                event['created_at'] = event['created_at'].isoformat()
            
            return jsonify({
                'success': True,
                'event': event
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Ni dogodka za datum {date}'
            }), 404
            
    except Exception as e:
        logger.error(f"Error fetching historical event for {date}: {e}")
        return jsonify({
            'success': False,
            'error': 'Napaka pri pridobivanju dogodka'
        }), 500

@app.route('/api/history/random')
@login_required
def random_history():
    """Get random historical event"""
    try:
        from ai_services.content_generator_sqlalchemy import HistoricalEventGenerator
        from ai_services.deepseek_client import DeepSeekClient
        
        ai_client = DeepSeekClient()
        event_generator = HistoricalEventGenerator(db, HistoricalEvent, ai_client)
        
        event = event_generator.get_random_event()
        
        if event:
            # Convert ObjectId to string for JSON serialization
            if '_id' in event:
                event['_id'] = str(event['_id'])
            if 'created_at' in event:
                event['created_at'] = event['created_at'].isoformat()
            
            return jsonify({
                'success': True,
                'event': event
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ni naključnega dogodka'
            }), 404
            
    except Exception as e:
        logger.error(f"Error fetching random historical event: {e}")
        return jsonify({
            'success': False,
            'error': 'Napaka pri pridobivanju dogodka'
        }), 500

@app.route('/api/history/featured')
@login_required
def featured_history():
    """Get featured historical events"""
    try:
        from ai_services.content_generator_sqlalchemy import HistoricalEventGenerator
        from ai_services.deepseek_client import DeepSeekClient
        
        ai_client = DeepSeekClient()
        event_generator = HistoricalEventGenerator(db, HistoricalEvent, ai_client)
        
        events = event_generator.get_featured_events(limit=5)
        
        # Convert ObjectIds to strings for JSON serialization
        for event in events:
            if '_id' in event:
                event['_id'] = str(event['_id'])
            if 'created_at' in event:
                event['created_at'] = event['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'events': events,
            'count': len(events)
        })
        
    except Exception as e:
        logger.error(f"Error fetching featured historical events: {e}")
        return jsonify({
            'success': False,
            'error': 'Napaka pri pridobivanju dogodkov'
        }), 500

# Trip Reports routes
@app.route('/trip-reports')
@login_required
def trip_reports():
    page = request.args.get('page', 1, type=int)
    per_page = 6  # 6 trip reports per page
    
    # Get total count for pagination
    total = TripReport.query.count()
    
    # Get trip reports with pagination
    trip_reports = TripReport.query.order_by(TripReport.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    # Calculate pagination
    has_prev = page > 1
    has_next = (page * per_page) < total
    prev_num = page - 1 if has_prev else None
    next_num = page + 1 if has_next else None
    
    return render_template('trip_reports.html', 
                         trip_reports=trip_reports,
                         has_prev=has_prev,
                         has_next=has_next,
                         prev_num=prev_num,
                         next_num=next_num,
                         page=page)

@app.route('/trip-reports/create', methods=['GET', 'POST'])
@login_required
def create_trip_report():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        date = request.form.get('date')
        difficulty = request.form.get('difficulty')
        
        if not all([title, description, location, date]):
            flash('Please fill in all required fields', 'error')
            return render_template('create_trip_report.html')
        
        # Handle file uploads
        uploaded_photos = []
        files = request.files.getlist('photos')
        
        for file in files:
            if file and file.filename:
                try:
                    # Check file size (10MB limit)
                    file.seek(0, 2)  # Seek to end
                    file_size = file.tell()
                    file.seek(0)  # Reset to beginning
                    
                    if file_size > 10 * 1024 * 1024:  # 10MB
                        flash(f'Datoteka {file.filename} je prevelika (max 10MB)', 'warning')
                        continue
                    
                    # Process and upload image
                    result = image_handler.process_and_upload_image(file, "trip_reports")
                    
                    uploaded_photos.append({
                        'key': result['key'],
                        'thumb_key': result['thumb_key'],
                        'url': result['url'],
                        'thumbnail_url': result['thumbnail_url'],
                        'width': result['width'],
                        'height': result['height']
                    })
                    
                except Exception as e:
                    logger.error(f"Error uploading image: {e}")
                    flash('Napaka pri nalaganju slike', 'warning')
        
        # Parse date
        try:
            trip_date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format', 'error')
            return render_template('create_trip_report.html')
        
        # Create trip report
        new_trip_report = TripReport(
            title=title,
            description=description,
            location=location,
            date=trip_date.date(),
            difficulty=difficulty,
            images=uploaded_photos,  # Store as JSON array
            author_id=session['user_id'],
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_trip_report)
        db.session.commit()
        flash('Trip report created successfully!', 'success')
        logger.info(f"User {session['user_name']} created trip report: {title}")
        
        return redirect(url_for('view_trip_report', trip_id=new_trip_report.id))
    
    return render_template('create_trip_report.html')

@app.route('/trip-reports/<int:trip_id>')
@login_required
def view_trip_report(trip_id):
    try:
        trip_report = TripReport.query.get(trip_id)
        if not trip_report:
            flash('Trip report not found', 'error')
            return redirect(url_for('trip_reports'))
        
        return render_template('view_trip_report.html', trip_report=trip_report)
    
    except Exception as e:
        logger.error(f"Error viewing trip report {trip_id}: {e}")
        flash('Error loading trip report', 'error')
        return redirect(url_for('trip_reports'))

@app.route('/trip-reports/<int:trip_id>/delete')
@login_required
def delete_trip_report(trip_id):
    try:
        trip_report = TripReport.query.get(trip_id)
        
        if not trip_report:
            flash('Trip report not found', 'error')
            return redirect(url_for('trip_reports'))
        
        # Check if user owns the trip report or is admin
        if trip_report.author_id != session['user_id'] and not session.get('is_admin', False):
            flash('You can only delete your own trip reports', 'error')
            return redirect(url_for('trip_reports'))
        
        # Delete photos from S3
        for photo in trip_report.images or []:
            try:
                image_handler.delete_images(photo)
            except Exception as e:
                logger.error(f"Error deleting image from S3: {e}")
        
        # Delete trip report from database
        db.session.delete(trip_report)
        db.session.commit()
        flash('Trip report deleted successfully', 'success')
        logger.info(f"User {session['user_name']} deleted trip report: {trip_report.title}")
        
    except Exception as e:
        logger.error(f"Error deleting trip report {trip_id}: {e}")
        flash('Error deleting trip report', 'error')
        db.session.rollback()
    
    return redirect(url_for('trip_reports'))

# AI Content API routes
@app.route('/api/today-in-history')
@login_required
def get_today_in_history():
    """Get today's historical mountaineering event"""
    try:
        generator = get_historical_generator()
        event = generator.get_today_event()
        
        if event:
            return jsonify({'success': True, 'event': event})
        else:
            return jsonify({'success': False, 'error': 'No event found for today'}), 404
            
    except Exception as e:
        logger.error(f"Error getting today's historical event: {e}")
        return jsonify({'success': False, 'error': 'Failed to load historical event'}), 500

@app.route('/api/today-in-history/date/<date>')
@login_required
def get_historical_event_by_date(date):
    """Get historical event for specific date (MM-DD format)"""
    try:
        # Validate date format
        if not date or len(date) != 5 or date[2] != '-':
            return jsonify({'success': False, 'error': 'Invalid date format. Use MM-DD'}), 400
        
        generator = get_historical_generator()
        event = generator.get_today_event(date)
        
        if event:
            return jsonify({'success': True, 'event': event})
        else:
            return jsonify({'success': False, 'error': f'No event found for {date}'}), 404
            
    except Exception as e:
        logger.error(f"Error getting historical event for {date}: {e}")
        return jsonify({'success': False, 'error': 'Failed to load historical event'}), 500

@app.route('/api/today-in-history/random')
@login_required
def get_random_historical_event():
    """Get a random historical mountaineering event"""
    try:
        generator = get_historical_generator()
        event = generator.get_random_event()
        
        if event:
            return jsonify({'success': True, 'event': event})
        else:
            return jsonify({'success': False, 'error': 'No historical events available'}), 404
            
    except Exception as e:
        logger.error(f"Error getting random historical event: {e}")
        return jsonify({'success': False, 'error': 'Failed to load random event'}), 500

@app.route('/api/today-in-history/category/<category>')
@login_required
def get_historical_events_by_category(category):
    """Get historical events by category"""
    try:
        limit = request.args.get('limit', 10, type=int)
        generator = get_historical_generator()
        events = generator.get_events_by_category(category, limit)
        
        return jsonify({'success': True, 'events': events, 'category': category})
        
    except Exception as e:
        logger.error(f"Error getting events by category {category}: {e}")
        return jsonify({'success': False, 'error': 'Failed to load events'}), 500

@app.route('/api/today-in-history/search')
@login_required
def search_historical_events():
    """Search historical events"""
    try:
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify({'success': False, 'error': 'Search query is required'}), 400
        
        generator = get_historical_generator()
        events = generator.search_events(query, limit)
        
        return jsonify({'success': True, 'events': events, 'query': query})
        
    except Exception as e:
        logger.error(f"Error searching historical events: {e}")
        return jsonify({'success': False, 'error': 'Search failed'}), 500

# Admin routes for historical events
@app.route('/api/admin/historical-events/<int:event_id>/verify', methods=['POST'])
@admin_required
def verify_historical_event(event_id):
    """Mark historical event as verified (admin only)"""
    try:
        generator = get_historical_generator()
        success = generator.verify_event(event_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Event verified successfully'})
        else:
            return jsonify({'success': False, 'error': 'Event not found'}), 404
            
    except Exception as e:
        logger.error(f"Error verifying event {event_id}: {e}")
        return jsonify({'success': False, 'error': 'Failed to verify event'}), 500

@app.route('/api/admin/historical-events/<int:event_id>/feature', methods=['POST'])
@admin_required
def feature_historical_event(event_id):
    """Mark historical event as featured (admin only)"""
    try:
        generator = get_historical_generator()
        success = generator.mark_as_featured(event_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Event marked as featured'})
        else:
            return jsonify({'success': False, 'error': 'Event not found'}), 404
            
    except Exception as e:
        logger.error(f"Error featuring event {event_id}: {e}")
        return jsonify({'success': False, 'error': 'Failed to feature event'}), 500

@app.route('/api/admin/historical-events/generate-range', methods=['POST'])
@admin_required
def generate_historical_events_range():
    """Generate historical events for date range (admin only)"""
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'success': False, 'error': 'start_date and end_date required'}), 400
        
        generator = get_historical_generator()
        count = generator.generate_events_for_date_range(start_date, end_date)
        
        return jsonify({
            'success': True, 
            'message': f'Generated {count} historical events',
            'generated_count': count
        })
        
    except Exception as e:
        logger.error(f"Error generating event range: {e}")
        return jsonify({'success': False, 'error': 'Failed to generate events'}), 500

@app.route('/api/admin/historical-events/stats')
@admin_required
def get_historical_events_stats():
    """Get statistics about historical events (admin only)"""
    try:
        generator = get_historical_generator()
        stats = generator.get_statistics()
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"Error getting historical events stats: {e}")
        return jsonify({'success': False, 'error': 'Failed to get statistics'}), 500

# News API routes
@app.route('/api/news/latest')
@login_required
def get_latest_news():
    """Get latest curated news articles"""
    try:
        limit = request.args.get('limit', 5, type=int)
        category = request.args.get('category')
        
        curator = get_news_curator()
        articles = curator.get_latest_news(limit=limit, category=category)
        
        return jsonify({'success': True, 'articles': articles})
        
    except Exception as e:
        logger.error(f"Error getting latest news: {e}")
        return jsonify({'success': False, 'error': 'Failed to load news'}), 500

@app.route('/api/news/category/<category>')
@login_required
def get_news_by_category(category):
    """Get news articles by category"""
    try:
        limit = request.args.get('limit', 5, type=int)
        
        curator = get_news_curator()
        articles = curator.get_latest_news(limit=limit, category=category)
        
        return jsonify({'success': True, 'articles': articles, 'category': category})
        
    except Exception as e:
        logger.error(f"Error getting news by category {category}: {e}")
        return jsonify({'success': False, 'error': 'Failed to load news'}), 500

@app.route('/api/news/categories')
@login_required
def get_news_by_categories():
    """Get news grouped by all categories"""
    try:
        curator = get_news_curator()
        articles_by_category = curator.get_news_by_category()
        
        return jsonify({'success': True, 'categories': articles_by_category})
        
    except Exception as e:
        logger.error(f"Error getting news by categories: {e}")
        return jsonify({'success': False, 'error': 'Failed to load news'}), 500

# Admin routes for news
@app.route('/api/admin/news/update', methods=['POST'])
@admin_required
def update_news_feed():
    """Manually trigger news update (admin only)"""
    try:
        curator = get_news_curator()
        stats = curator.fetch_and_process_feeds()
        
        return jsonify({
            'success': True, 
            'message': 'News feed updated successfully',
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error updating news feed: {e}")
        return jsonify({'success': False, 'error': 'Failed to update news feed'}), 500

@app.route('/api/admin/news/stats')
@admin_required
def get_news_stats():
    """Get news curation statistics (admin only)"""
    try:
        curator = get_news_curator()
        stats = curator.get_statistics()
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"Error getting news stats: {e}")
        return jsonify({'success': False, 'error': 'Failed to get statistics'}), 500

# Temporary admin creation endpoint
@app.route('/create-admin-temp')
def create_admin_temp():
    try:
        admin = User.query.filter_by(email='admin@mountaineering.club').first()
        if admin:
            return 'Admin already exists!'
        
        admin = User(
            email='admin@mountaineering.club',
            password_hash=generate_password_hash('admin123'),
            first_name='Admin',
            last_name='User',
            is_admin=True,
            is_approved=True,
            is_email_verified=True
        )
        
        db.session.add(admin)
        db.session.commit()
        return 'Admin created! Email: admin@mountaineering.club, Password: admin123'
    except Exception as e:
        return f'Error: {str(e)}'

# Temporary table creation endpoint
@app.route('/create-tables-temp')
def create_tables_temp():
    try:
        db.create_all()
        return 'All tables created successfully!'
    except Exception as e:
        return f'Error creating tables: {str(e)}'

# Test S3 connection
@app.route('/test-s3-temp')
def test_s3_temp():
    try:
        from image_handler import ImageHandler
        handler = ImageHandler()
        
        # Test S3 connection
        response = handler.s3_client.list_objects_v2(Bucket=handler.bucket_name, MaxKeys=1)
        return f'S3 connection OK! Bucket: {handler.bucket_name}, Region: {handler.s3_client.meta.region_name}'
    except Exception as e:
        return f'S3 Error: {str(e)}'

# Trip Planning routes
@app.route('/planned-trips')
@login_required
def planned_trips():
    # Get upcoming trips
    from datetime import datetime
    current_date = datetime.utcnow()
    
    upcoming_trips = PlannedTrip.query.filter(
        PlannedTrip.trip_date >= current_date
    ).order_by(PlannedTrip.trip_date.asc()).all()
    
    # Get past trips for reference
    past_trips = PlannedTrip.query.filter(
        PlannedTrip.trip_date < current_date
    ).order_by(PlannedTrip.trip_date.desc()).limit(10).all()
    
    return render_template('planned_trips.html', 
                         upcoming_trips=upcoming_trips,
                         past_trips=past_trips)

@app.route('/planned-trips/create', methods=['GET', 'POST'])
@admin_required
def create_planned_trip():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        trip_date = request.form.get('trip_date')
        difficulty = request.form.get('difficulty')
        max_participants = request.form.get('max_participants')
        meeting_point = request.form.get('meeting_point')
        meeting_time = request.form.get('meeting_time')
        estimated_duration = request.form.get('estimated_duration')
        price = request.form.get('price', 0)
        
        if not all([title, description, location, trip_date, meeting_point]):
            flash('Prosimo, izpolnite vsa obvezna polja', 'error')
            return render_template('create_planned_trip.html')
        
        # Parse date and time
        try:
            trip_datetime = datetime.strptime(f"{trip_date} {meeting_time or '09:00'}", '%Y-%m-%d %H:%M')
        except ValueError:
            flash('Neveljaven datum ali čas', 'error')
            return render_template('create_planned_trip.html')
        
        # Create planned trip
        new_trip = PlannedTrip(
            title=title,
            description=description,
            location=location,
            trip_date=trip_datetime,
            difficulty=difficulty,
            max_participants=int(max_participants) if max_participants else None,
            meeting_point=meeting_point,
            estimated_duration=estimated_duration,
            price=float(price) if price else 0,
            organizer_id=session['user_id'],
            status='open',  # open, full, cancelled, completed
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_trip)
        db.session.commit()
        flash('Izlet je bil uspešno ustvarjen!', 'success')
        logger.info(f"Admin {session['user_name']} created planned trip: {title}")
        
        return redirect(url_for('view_planned_trip', trip_id=new_trip.id))
    
    return render_template('create_planned_trip.html')

@app.route('/planned-trips/<int:trip_id>')
@login_required
def view_planned_trip(trip_id):
    try:
        trip = PlannedTrip.query.get(trip_id)
        if not trip:
            flash('Izlet ni bil najden', 'error')
            return redirect(url_for('planned_trips'))
        
        # Check if current user is registered
        user_registered = any(p.user_id == session['user_id'] for p in trip.participants)
        
        # Check if trip is in the future
        is_future = trip.trip_date > datetime.utcnow()
        
        return render_template('view_planned_trip.html', 
                             trip=trip, 
                             user_registered=user_registered,
                             is_future=is_future)
    
    except Exception as e:
        logger.error(f"Error viewing planned trip {trip_id}: {e}")
        flash('Napaka pri nalaganju izleta', 'error')
        return redirect(url_for('planned_trips'))

@app.route('/planned-trips/<int:trip_id>/register', methods=['POST'])
@login_required
def register_for_trip(trip_id):
    try:
        trip = PlannedTrip.query.get(trip_id)
        if not trip:
            flash('Izlet ni bil najden', 'error')
            return redirect(url_for('planned_trips'))
        
        # Check if already registered
        if any(p.user_id == session['user_id'] for p in trip.participants):
            flash('Že ste prijavljeni na ta izlet', 'warning')
            return redirect(url_for('view_planned_trip', trip_id=trip_id))
        
        # Check if trip is full
        if trip.max_participants and len(trip.participants) >= trip.max_participants:
            flash('Izlet je poln', 'error')
            return redirect(url_for('view_planned_trip', trip_id=trip_id))
        
        # Check if trip date has passed
        if trip.trip_date < datetime.utcnow():
            flash('Na pretekle izlete se ne morete več prijaviti', 'error')
            return redirect(url_for('view_planned_trip', trip_id=trip_id))
        
        # Register user
        participant = TripParticipant(
            user_id=session['user_id'],
            trip_id=trip_id,
            phone=request.form.get('phone', ''),
            emergency_contact=request.form.get('emergency_contact', ''),
            notes=request.form.get('notes', ''),
            registered_at=datetime.utcnow()
        )
        
        db.session.add(participant)
        db.session.commit()
        
        flash('Uspešno ste se prijavili na izlet!', 'success')
        logger.info(f"User {session['user_name']} registered for trip: {trip.title}")
        
    except Exception as e:
        logger.error(f"Error registering for trip {trip_id}: {e}")
        flash('Napaka pri prijavi na izlet', 'error')
        db.session.rollback()
    
    return redirect(url_for('view_planned_trip', trip_id=trip_id))

@app.route('/planned-trips/<int:trip_id>/unregister', methods=['POST'])
@login_required
def unregister_from_trip(trip_id):
    try:
        trip = PlannedTrip.query.get(trip_id)
        if not trip:
            flash('Izlet ni bil najden', 'error')
            return redirect(url_for('planned_trips'))
        
        # Check if trip date has passed
        if trip.trip_date < datetime.utcnow():
            flash('S preteklih izletov se ne morete več odjaviti', 'error')
            return redirect(url_for('view_planned_trip', trip_id=trip_id))
        
        # Remove user from participants
        participant = TripParticipant.query.filter_by(
            trip_id=trip_id,
            user_id=session['user_id']
        ).first()
        
        if participant:
            db.session.delete(participant)
            db.session.commit()
            flash('Uspešno ste se odjavili z izleta', 'success')
            logger.info(f"User {session['user_name']} unregistered from trip: {trip.title}")
        else:
            flash('Niste prijavljeni na ta izlet', 'warning')
        
    except Exception as e:
        logger.error(f"Error unregistering from trip {trip_id}: {e}")
        flash('Napaka pri odjavi z izleta', 'error')
        db.session.rollback()
    
    return redirect(url_for('view_planned_trip', trip_id=trip_id))

@app.route('/planned-trips/<int:trip_id>/gear', methods=['POST'])
@admin_required
def update_gear_list(trip_id):
    try:
        gear_items = request.form.get('gear_items', '').split('\n')
        gear_list = [item.strip() for item in gear_items if item.strip()]
        
        trip = PlannedTrip.query.get(trip_id)
        if trip:
            trip.gear_list = gear_list
            db.session.commit()
            flash('Seznam opreme je bil posodobljen', 'success')
        else:
            flash('Izlet ni bil najden', 'error')
        
    except Exception as e:
        logger.error(f"Error updating gear list for trip {trip_id}: {e}")
        flash('Napaka pri posodabljanju seznama opreme', 'error')
        db.session.rollback()
    
    return redirect(url_for('view_planned_trip', trip_id=trip_id))

# Background task for news updates
import threading
import time

def news_update_scheduler():
    """Background task to update news every 24 hours at 6 AM"""
    
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
                    curator = get_news_curator()
                    stats = curator.fetch_and_process_feeds()
                    logger.info(f"Scheduled news update completed: {stats}")
                except Exception as e:
                    logger.error(f"Scheduled news update failed: {e}")
            
        except Exception as e:
            logger.error(f"News scheduler error: {e}")
            # Sleep for 1 hour before retrying
            time.sleep(3600)

# Start background news scheduler
def start_background_tasks():
    """Start background tasks"""
    if os.environ.get('FLASK_ENV') != 'development':
        # Only run scheduler in production
        news_thread = threading.Thread(target=news_update_scheduler, daemon=True)
        news_thread.start()
        logger.info("Background news scheduler started")

# WebSocket events for chat removed - feature cancelled

if __name__ == '__main__':
    # Start background tasks
    start_background_tasks()
    
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=True, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)