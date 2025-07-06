from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson import ObjectId
import os
from datetime import datetime
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

app = Flask(__name__)

# Basic Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/mountaineering_club')
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
mongo = PyMongo(app)
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
    client_id=os.environ.get('FACEBOOK_CLIENT_ID'),
    client_secret=os.environ.get('FACEBOOK_CLIENT_SECRET'),
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
        user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
        if not user or not user.get('is_admin', False):
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
        mongo.db.users.count_documents({})
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
        announcements = list(mongo.db.announcements.find().sort('created_at', -1).limit(3))
    except Exception as e:
        logger.error(f"MongoDB error: {e}")
        announcements = []
    return render_template('home.html', announcements=announcements)

@app.route('/dashboard')
@login_required
def dashboard():
    user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    announcements = list(mongo.db.announcements.find().sort('created_at', -1).limit(5))
    recent_trips = list(mongo.db.trip_reports.find().sort('created_at', -1).limit(5))
    return render_template('dashboard.html', user=user, announcements=announcements, recent_trips=recent_trips)

@app.route('/register', methods=['GET', 'POST'])
# @limiter.limit("5 per minute")  # Disabled with Redis
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        # Check if user exists
        if mongo.db.users.find_one({'email': email}):
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user (pending approval)
        user_data = {
            'email': email,
            'password': generate_password_hash(password),
            'full_name': full_name,
            'is_approved': False,
            'is_admin': False,
            'created_at': datetime.utcnow(),
            'profile_picture': None
        }
        
        result = mongo.db.users.insert_one(user_data)
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
        
        user = mongo.db.users.find_one({'email': email})
        
        if user and check_password_hash(user['password'], password):
            if not user.get('is_approved', False):
                flash('Account pending approval', 'warning')
                return render_template('login.html')
            
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['full_name']
            session['is_admin'] = user.get('is_admin', False)
            
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
        user = mongo.db.users.find_one({'email': email})
        
        if user:
            # User exists - log them in
            if not user.get('is_approved', False):
                flash('Vaš račun še čaka na odobritev skrbnika', 'warning')
                return redirect(url_for('login'))
            
            # Update profile picture if available
            if profile_picture and not user.get('profile_picture'):
                mongo.db.users.update_one(
                    {'_id': user['_id']},
                    {'$set': {'profile_picture': profile_picture}}
                )
            
            # Log user in
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['full_name']
            session['is_admin'] = user.get('is_admin', False)
            
            logger.info(f"User logged in via {provider}: {email}")
            flash(f'Uspešno ste se prijavili preko {provider.title()}', 'success')
            return redirect(url_for('dashboard'))
        
        else:
            # Create new user account (pending approval)
            user_data = {
                'email': email,
                'full_name': full_name,
                'password': None,  # OAuth users don't have passwords
                'oauth_provider': provider,
                'profile_picture': profile_picture,
                'is_approved': False,
                'is_admin': False,
                'created_at': datetime.utcnow()
            }
            
            result = mongo.db.users.insert_one(user_data)
            logger.info(f"New OAuth user registered via {provider}: {email}")
            
            flash(f'Račun ustvarjen preko {provider.title()}! Prosimo, počakajte na odobritev skrbnika.', 'success')
            return redirect(url_for('login'))
    
    except Exception as e:
        logger.error(f"OAuth {provider} error: {e}")
        flash('Napaka pri prijavi. Poskusite znova.', 'error')
        return redirect(url_for('login'))

# Admin routes
@app.route('/admin')
@admin_required
def admin_panel():
    pending_users = list(mongo.db.users.find({'is_approved': False}).sort('created_at', -1))
    all_users = list(mongo.db.users.find().sort('created_at', -1))
    stats = {
        'total_users': mongo.db.users.count_documents({}),
        'pending_approval': mongo.db.users.count_documents({'is_approved': False}),
        'approved_users': mongo.db.users.count_documents({'is_approved': True}),
        'admin_users': mongo.db.users.count_documents({'is_admin': True})
    }
    return render_template('admin_panel.html', 
                         pending_users=pending_users, 
                         all_users=all_users, 
                         stats=stats)

@app.route('/admin/approve_user/<user_id>')
@admin_required
def approve_user(user_id):
    try:
        result = mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'is_approved': True}}
        )
        if result.modified_count:
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            flash(f'User {user["full_name"]} approved successfully', 'success')
            logger.info(f"Admin {session['user_name']} approved user {user['email']}")
        else:
            flash('User not found', 'error')
    except Exception as e:
        flash('Error approving user', 'error')
        logger.error(f"Error approving user {user_id}: {e}")
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject_user/<user_id>')
@admin_required
def reject_user(user_id):
    try:
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if user:
            mongo.db.users.delete_one({'_id': ObjectId(user_id)})
            flash(f'User {user["full_name"]} rejected and removed', 'warning')
            logger.info(f"Admin {session['user_name']} rejected user {user['email']}")
        else:
            flash('User not found', 'error')
    except Exception as e:
        flash('Error rejecting user', 'error')
        logger.error(f"Error rejecting user {user_id}: {e}")
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/toggle_admin/<user_id>')
@admin_required
def toggle_admin(user_id):
    try:
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if user:
            new_admin_status = not user.get('is_admin', False)
            mongo.db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'is_admin': new_admin_status}}
            )
            action = 'promoted to' if new_admin_status else 'removed from'
            flash(f'{user["full_name"]} {action} admin', 'success')
            logger.info(f"Admin {session['user_name']} changed admin status for {user['email']}")
        else:
            flash('User not found', 'error')
    except Exception as e:
        flash('Error updating admin status', 'error')
        logger.error(f"Error toggling admin for {user_id}: {e}")
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/announcements')
@admin_required
def admin_announcements():
    announcements = list(mongo.db.announcements.find().sort('created_at', -1))
    return render_template('admin_announcements.html', announcements=announcements)

@app.route('/admin/announcements/create', methods=['GET', 'POST'])
@admin_required
def create_announcement():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if title and content:
            announcement_data = {
                'title': title,
                'content': content,
                'author_id': session['user_id'],
                'author_name': session['user_name'],
                'created_at': datetime.utcnow()
            }
            
            mongo.db.announcements.insert_one(announcement_data)
            flash('Announcement created successfully', 'success')
            logger.info(f"Admin {session['user_name']} created announcement: {title}")
            return redirect(url_for('admin_announcements'))
        else:
            flash('Title and content are required', 'error')
    
    return render_template('create_announcement.html')

@app.route('/admin/announcements/delete/<announcement_id>')
@admin_required
def delete_announcement(announcement_id):
    try:
        announcement = mongo.db.announcements.find_one({'_id': ObjectId(announcement_id)})
        if announcement:
            mongo.db.announcements.delete_one({'_id': ObjectId(announcement_id)})
            flash('Announcement deleted successfully', 'success')
            logger.info(f"Admin {session['user_name']} deleted announcement: {announcement['title']}")
        else:
            flash('Announcement not found', 'error')
    except Exception as e:
        flash('Error deleting announcement', 'error')
        logger.error(f"Error deleting announcement {announcement_id}: {e}")
    
    return redirect(url_for('admin_announcements'))

# Comments routes
@app.route('/api/comments/<content_type>/<content_id>')
@login_required
def get_comments(content_type, content_id):
    """Get comments for announcements or trip reports"""
    try:
        if content_type not in ['announcement', 'trip_report']:
            return jsonify({'error': 'Invalid content type'}), 400
        
        comments = list(mongo.db.comments.find({
            'content_type': content_type,
            'content_id': content_id
        }).sort('created_at', 1))
        
        # Convert ObjectId to string for JSON serialization
        for comment in comments:
            comment['_id'] = str(comment['_id'])
            comment['created_at'] = comment['created_at'].isoformat()
        
        return jsonify({'comments': comments})
    
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
            content = mongo.db.announcements.find_one({'_id': ObjectId(content_id)})
        else:  # trip_report
            content = mongo.db.trip_reports.find_one({'_id': ObjectId(content_id)})
        
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        comment_data = {
            'content_type': content_type,
            'content_id': content_id,
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'comment': comment_text,
            'created_at': datetime.utcnow()
        }
        
        result = mongo.db.comments.insert_one(comment_data)
        
        # Return the new comment
        comment_data['_id'] = str(result.inserted_id)
        comment_data['created_at'] = comment_data['created_at'].isoformat()
        
        logger.info(f"User {session['user_name']} added comment to {content_type} {content_id}")
        
        return jsonify({'comment': comment_data}), 201
    
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        return jsonify({'error': 'Error adding comment'}), 500

@app.route('/api/comments/<comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Delete a comment (only by author or admin)"""
    try:
        comment = mongo.db.comments.find_one({'_id': ObjectId(comment_id)})
        
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        # Check if user can delete this comment
        if comment['user_id'] != session['user_id'] and not session.get('is_admin', False):
            return jsonify({'error': 'Not authorized to delete this comment'}), 403
        
        mongo.db.comments.delete_one({'_id': ObjectId(comment_id)})
        
        logger.info(f"User {session['user_name']} deleted comment {comment_id}")
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Error deleting comment: {e}")
        return jsonify({'error': 'Error deleting comment'}), 500

# Trip Reports routes
@app.route('/trip-reports')
@login_required
def trip_reports():
    page = request.args.get('page', 1, type=int)
    per_page = 6  # 6 trip reports per page
    
    # Get total count for pagination
    total = mongo.db.trip_reports.count_documents({})
    
    # Get trip reports with pagination
    trip_reports = list(mongo.db.trip_reports.find()
                       .sort('created_at', -1)
                       .skip((page - 1) * per_page)
                       .limit(per_page))
    
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
        trip_report_data = {
            'title': title,
            'description': description,
            'location': location,
            'trip_date': trip_date,
            'difficulty': difficulty,
            'photos': uploaded_photos,
            'author_id': session['user_id'],
            'author_name': session['user_name'],
            'created_at': datetime.utcnow()
        }
        
        result = mongo.db.trip_reports.insert_one(trip_report_data)
        flash('Trip report created successfully!', 'success')
        logger.info(f"User {session['user_name']} created trip report: {title}")
        
        return redirect(url_for('view_trip_report', trip_id=result.inserted_id))
    
    return render_template('create_trip_report.html')

@app.route('/trip-reports/<trip_id>')
@login_required
def view_trip_report(trip_id):
    try:
        trip_report = mongo.db.trip_reports.find_one({'_id': ObjectId(trip_id)})
        if not trip_report:
            flash('Trip report not found', 'error')
            return redirect(url_for('trip_reports'))
        
        return render_template('view_trip_report.html', trip_report=trip_report)
    
    except Exception as e:
        logger.error(f"Error viewing trip report {trip_id}: {e}")
        flash('Error loading trip report', 'error')
        return redirect(url_for('trip_reports'))

@app.route('/trip-reports/<trip_id>/delete')
@login_required
def delete_trip_report(trip_id):
    try:
        trip_report = mongo.db.trip_reports.find_one({'_id': ObjectId(trip_id)})
        
        if not trip_report:
            flash('Trip report not found', 'error')
            return redirect(url_for('trip_reports'))
        
        # Check if user owns the trip report or is admin
        if trip_report['author_id'] != session['user_id'] and not session.get('is_admin', False):
            flash('You can only delete your own trip reports', 'error')
            return redirect(url_for('trip_reports'))
        
        # Delete photos from S3
        for photo in trip_report.get('photos', []):
            try:
                image_handler.delete_images(photo)
            except Exception as e:
                logger.error(f"Error deleting image from S3: {e}")
        
        # Delete trip report from database
        mongo.db.trip_reports.delete_one({'_id': ObjectId(trip_id)})
        flash('Trip report deleted successfully', 'success')
        logger.info(f"User {session['user_name']} deleted trip report: {trip_report['title']}")
        
    except Exception as e:
        logger.error(f"Error deleting trip report {trip_id}: {e}")
        flash('Error deleting trip report', 'error')
    
    return redirect(url_for('trip_reports'))

# Chat routes
@app.route('/chat')
@login_required
def chat():
    # Get recent chat messages
    recent_messages = list(mongo.db.chat_messages.find()
                          .sort('timestamp', -1)
                          .limit(50))
    recent_messages.reverse()  # Oldest first for display
    
    # Get online users (simplified - just show recent activity)
    online_users = list(mongo.db.users.find(
        {'is_approved': True}, 
        {'full_name': 1, 'email': 1}
    ).limit(20))
    
    return render_template('chat.html', 
                         recent_messages=recent_messages,
                         online_users=online_users)

@app.route('/api/chat/history')
@login_required
def chat_history():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    messages = list(mongo.db.chat_messages.find()
                   .sort('timestamp', -1)
                   .skip((page - 1) * per_page)
                   .limit(per_page))
    
    messages.reverse()  # Oldest first
    
    # Convert ObjectId to string for JSON serialization
    for msg in messages:
        msg['_id'] = str(msg['_id'])
        msg['timestamp'] = msg['timestamp'].isoformat()
    
    return jsonify({
        'messages': messages,
        'has_more': len(messages) == per_page
    })

# Trip Planning routes
@app.route('/planned-trips')
@login_required
def planned_trips():
    # Get upcoming trips
    from datetime import datetime
    current_date = datetime.utcnow()
    
    upcoming_trips = list(mongo.db.planned_trips.find({
        'trip_date': {'$gte': current_date}
    }).sort('trip_date', 1))
    
    # Get past trips for reference
    past_trips = list(mongo.db.planned_trips.find({
        'trip_date': {'$lt': current_date}
    }).sort('trip_date', -1).limit(10))
    
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
        trip_data = {
            'title': title,
            'description': description,
            'location': location,
            'trip_date': trip_datetime,
            'difficulty': difficulty,
            'max_participants': int(max_participants) if max_participants else None,
            'meeting_point': meeting_point,
            'estimated_duration': estimated_duration,
            'price': float(price) if price else 0,
            'trip_leader_id': session['user_id'],
            'trip_leader_name': session['user_name'],
            'participants': [],
            'gear_list': [],
            'carpools': [],
            'created_at': datetime.utcnow(),
            'status': 'open'  # open, full, cancelled, completed
        }
        
        result = mongo.db.planned_trips.insert_one(trip_data)
        flash('Izlet je bil uspešno ustvarjen!', 'success')
        logger.info(f"Admin {session['user_name']} created planned trip: {title}")
        
        return redirect(url_for('view_planned_trip', trip_id=result.inserted_id))
    
    return render_template('create_planned_trip.html')

@app.route('/planned-trips/<trip_id>')
@login_required
def view_planned_trip(trip_id):
    try:
        trip = mongo.db.planned_trips.find_one({'_id': ObjectId(trip_id)})
        if not trip:
            flash('Izlet ni bil najden', 'error')
            return redirect(url_for('planned_trips'))
        
        # Check if current user is registered
        user_registered = any(p.get('user_id') == session['user_id'] for p in trip.get('participants', []))
        
        # Check if trip is in the future
        is_future = trip['trip_date'] > datetime.utcnow()
        
        # Get weather data if we have coordinates (placeholder for now)
        weather_data = None
        
        return render_template('view_planned_trip.html', 
                             trip=trip, 
                             user_registered=user_registered,
                             is_future=is_future,
                             weather_data=weather_data)
    
    except Exception as e:
        logger.error(f"Error viewing planned trip {trip_id}: {e}")
        flash('Napaka pri nalaganju izleta', 'error')
        return redirect(url_for('planned_trips'))

@app.route('/planned-trips/<trip_id>/register', methods=['POST'])
@login_required
def register_for_trip(trip_id):
    try:
        trip = mongo.db.planned_trips.find_one({'_id': ObjectId(trip_id)})
        if not trip:
            flash('Izlet ni bil najden', 'error')
            return redirect(url_for('planned_trips'))
        
        # Check if already registered
        if any(p.get('user_id') == session['user_id'] for p in trip.get('participants', [])):
            flash('Že ste prijavljeni na ta izlet', 'warning')
            return redirect(url_for('view_planned_trip', trip_id=trip_id))
        
        # Check if trip is full
        max_participants = trip.get('max_participants')
        current_participants = len(trip.get('participants', []))
        
        if max_participants and current_participants >= max_participants:
            flash('Izlet je poln', 'error')
            return redirect(url_for('view_planned_trip', trip_id=trip_id))
        
        # Check if trip date has passed
        if trip['trip_date'] < datetime.utcnow():
            flash('Na pretekle izlete se ne morete več prijaviti', 'error')
            return redirect(url_for('view_planned_trip', trip_id=trip_id))
        
        # Register user
        participant_data = {
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'registered_at': datetime.utcnow(),
            'phone': request.form.get('phone', ''),
            'emergency_contact': request.form.get('emergency_contact', ''),
            'notes': request.form.get('notes', '')
        }
        
        mongo.db.planned_trips.update_one(
            {'_id': ObjectId(trip_id)},
            {'$push': {'participants': participant_data}}
        )
        
        flash('Uspešno ste se prijavili na izlet!', 'success')
        logger.info(f"User {session['user_name']} registered for trip: {trip['title']}")
        
    except Exception as e:
        logger.error(f"Error registering for trip {trip_id}: {e}")
        flash('Napaka pri prijavi na izlet', 'error')
    
    return redirect(url_for('view_planned_trip', trip_id=trip_id))

@app.route('/planned-trips/<trip_id>/unregister', methods=['POST'])
@login_required
def unregister_from_trip(trip_id):
    try:
        trip = mongo.db.planned_trips.find_one({'_id': ObjectId(trip_id)})
        if not trip:
            flash('Izlet ni bil najden', 'error')
            return redirect(url_for('planned_trips'))
        
        # Check if trip date has passed
        if trip['trip_date'] < datetime.utcnow():
            flash('S preteklih izletov se ne morete več odjaviti', 'error')
            return redirect(url_for('view_planned_trip', trip_id=trip_id))
        
        # Remove user from participants
        mongo.db.planned_trips.update_one(
            {'_id': ObjectId(trip_id)},
            {'$pull': {'participants': {'user_id': session['user_id']}}}
        )
        
        flash('Uspešno ste se odjavili z izleta', 'success')
        logger.info(f"User {session['user_name']} unregistered from trip: {trip['title']}")
        
    except Exception as e:
        logger.error(f"Error unregistering from trip {trip_id}: {e}")
        flash('Napaka pri odjavi z izleta', 'error')
    
    return redirect(url_for('view_planned_trip', trip_id=trip_id))

@app.route('/planned-trips/<trip_id>/gear', methods=['POST'])
@admin_required
def update_gear_list(trip_id):
    try:
        gear_items = request.form.get('gear_items', '').split('\n')
        gear_list = [item.strip() for item in gear_items if item.strip()]
        
        mongo.db.planned_trips.update_one(
            {'_id': ObjectId(trip_id)},
            {'$set': {'gear_list': gear_list}}
        )
        
        flash('Seznam opreme je bil posodobljen', 'success')
        
    except Exception as e:
        logger.error(f"Error updating gear list for trip {trip_id}: {e}")
        flash('Napaka pri posodabljanju seznama opreme', 'error')
    
    return redirect(url_for('view_planned_trip', trip_id=trip_id))

# WebSocket events for chat
@socketio.on('join')
def on_join(data):
    if 'user_id' not in session:
        return False
    
    username = session.get('user_name', 'Anonymous')
    join_room('main_chat')
    emit('status', {'msg': f'{username} has joined the chat'}, room='main_chat')

@socketio.on('leave')
def on_leave(data):
    if 'user_id' not in session:
        return False
    
    username = session.get('user_name', 'Anonymous')
    leave_room('main_chat')
    emit('status', {'msg': f'{username} has left the chat'}, room='main_chat')

@socketio.on('message')
# @limiter.limit("30 per minute")  # Temporarily disabled
def handle_message(data):
    if 'user_id' not in session:
        return False
    
    message_data = {
        'user_id': session['user_id'],
        'username': session.get('user_name', 'Anonymous'),
        'message': data['message'],
        'timestamp': datetime.utcnow()
    }
    
    # Save to database
    mongo.db.chat_messages.insert_one(message_data)
    
    # Emit to all users in chat room
    emit('message', {
        'username': message_data['username'],
        'message': message_data['message'],
        'timestamp': message_data['timestamp'].isoformat()
    }, room='main_chat')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)