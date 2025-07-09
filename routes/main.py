"""
Main routes for the application (home, dashboard, etc.).
"""
from flask import Blueprint, render_template, session, jsonify
from datetime import datetime
import logging

from models import User, Announcement, TripReport
from utils.decorators import login_required
from utils.helpers import handle_error

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    """Home page with recent announcements."""
    try:
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all()
    except Exception as e:
        logger.error(f"Database error: {e}")
        announcements = []
    
    return render_template('home.html', announcements=announcements)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with announcements and recent trips."""
    try:
        user = User.query.get(session['user_id'])
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
        recent_trips = TripReport.query.order_by(TripReport.created_at.desc()).limit(5).all()
        
        return render_template('dashboard.html', 
                             user=user, 
                             announcements=announcements, 
                             recent_trips=recent_trips)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return handle_error('Error loading dashboard', 500)


@main_bp.route('/health')
def health_check():
    """Health check endpoint for deployment platforms."""
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