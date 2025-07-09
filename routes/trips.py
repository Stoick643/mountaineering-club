"""
Trip routes for trip reports and planned trips.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import logging

from services.trip_service import TripService
from utils.decorators import login_required, admin_required
from utils.helpers import handle_error
from image_handler import ImageHandler

logger = logging.getLogger(__name__)

trips_bp = Blueprint('trips', __name__)

# Initialize image handler
image_handler = ImageHandler()


@trips_bp.route('/trip-reports')
@login_required
def trip_reports():
    """Trip reports listing with pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        data = TripService.get_trip_reports(page=page)
        
        return render_template('trip_reports.html', 
                             trip_reports=data['trip_reports'],
                             has_prev=data['has_prev'],
                             has_next=data['has_next'],
                             prev_num=data['prev_num'],
                             next_num=data['next_num'],
                             page=page)
    except Exception as e:
        logger.error(f"Error loading trip reports: {e}")
        flash('Error loading trip reports', 'error')
        return redirect(url_for('main.dashboard'))


@trips_bp.route('/trip-reports/create', methods=['GET', 'POST'])
@login_required
def create_trip_report():
    """Create a new trip report."""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        date = request.form.get('date')
        difficulty = request.form.get('difficulty')
        
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
                        flash(f'File {file.filename} is too large (max 10MB)', 'warning')
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
                    flash('Error uploading image', 'warning')
        
        success, message, trip_report = TripService.create_trip_report(
            title, description, location, date, difficulty, uploaded_photos
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('trips.view_trip_report', trip_id=trip_report.id))
        else:
            flash(message, 'error')
    
    return render_template('create_trip_report.html')


@trips_bp.route('/trip-reports/<int:trip_id>')
@login_required
def view_trip_report(trip_id):
    """View a specific trip report."""
    try:
        trip_report = TripService.get_trip_report(trip_id)
        if not trip_report:
            flash('Trip report not found', 'error')
            return redirect(url_for('trips.trip_reports'))
        
        return render_template('view_trip_report.html', trip_report=trip_report)
    
    except Exception as e:
        logger.error(f"Error viewing trip report {trip_id}: {e}")
        flash('Error loading trip report', 'error')
        return redirect(url_for('trips.trip_reports'))


@trips_bp.route('/trip-reports/<int:trip_id>/delete')
@login_required
def delete_trip_report(trip_id):
    """Delete a trip report."""
    try:
        trip_report = TripService.get_trip_report(trip_id)
        if not trip_report:
            flash('Trip report not found', 'error')
            return redirect(url_for('trips.trip_reports'))
        
        # Delete photos from S3
        for photo in trip_report.images or []:
            try:
                image_handler.delete_images(photo)
            except Exception as e:
                logger.error(f"Error deleting image from S3: {e}")
        
        success, message = TripService.delete_trip_report(trip_id)
        flash(message, 'success' if success else 'error')
        
    except Exception as e:
        logger.error(f"Error deleting trip report {trip_id}: {e}")
        flash('Error deleting trip report', 'error')
    
    return redirect(url_for('trips.trip_reports'))


@trips_bp.route('/planned-trips')
@login_required
def planned_trips():
    """Planned trips listing."""
    try:
        data = TripService.get_planned_trips()
        return render_template('planned_trips.html', 
                             upcoming_trips=data['upcoming_trips'],
                             past_trips=data['past_trips'])
    except Exception as e:
        logger.error(f"Error loading planned trips: {e}")
        flash('Error loading planned trips', 'error')
        return redirect(url_for('main.dashboard'))


@trips_bp.route('/planned-trips/create', methods=['GET', 'POST'])
@admin_required
def create_planned_trip():
    """Create a new planned trip."""
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
        
        success, message, trip = TripService.create_planned_trip(
            title, description, location, trip_date, difficulty,
            max_participants, meeting_point, meeting_time,
            estimated_duration, price
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('trips.view_planned_trip', trip_id=trip.id))
        else:
            flash(message, 'error')
    
    return render_template('create_planned_trip.html')


@trips_bp.route('/planned-trips/<int:trip_id>')
@login_required
def view_planned_trip(trip_id):
    """View a specific planned trip."""
    try:
        trip = TripService.get_planned_trip(trip_id)
        if not trip:
            flash('Trip not found', 'error')
            return redirect(url_for('trips.planned_trips'))
        
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
        flash('Error loading trip', 'error')
        return redirect(url_for('trips.planned_trips'))


@trips_bp.route('/planned-trips/<int:trip_id>/register', methods=['POST'])
@login_required
def register_for_trip(trip_id):
    """Register for a planned trip."""
    phone = request.form.get('phone', '')
    emergency_contact = request.form.get('emergency_contact', '')
    notes = request.form.get('notes', '')
    
    success, message = TripService.register_for_trip(
        trip_id, phone=phone, emergency_contact=emergency_contact, notes=notes
    )
    
    flash(message, 'success' if success else 'error')
    return redirect(url_for('trips.view_planned_trip', trip_id=trip_id))


@trips_bp.route('/planned-trips/<int:trip_id>/unregister', methods=['POST'])
@login_required
def unregister_from_trip(trip_id):
    """Unregister from a planned trip."""
    success, message = TripService.unregister_from_trip(trip_id)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('trips.view_planned_trip', trip_id=trip_id))


@trips_bp.route('/planned-trips/<int:trip_id>/gear', methods=['POST'])
@admin_required
def update_gear_list(trip_id):
    """Update gear list for a planned trip."""
    gear_items = request.form.get('gear_items', '')
    
    success, message = TripService.update_gear_list(trip_id, gear_items)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('trips.view_planned_trip', trip_id=trip_id))