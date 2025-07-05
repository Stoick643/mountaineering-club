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
import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit, join_room, leave_room
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/mountaineering_club')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

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

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
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
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))

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
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)