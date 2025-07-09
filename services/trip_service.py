"""
Trip service for managing trip reports and planned trips.
"""
from datetime import datetime
from flask import session
import logging

from models import db, TripReport, PlannedTrip, TripParticipant, User

logger = logging.getLogger(__name__)


class TripService:
    """Service for handling trip reports and planned trips."""
    
    @staticmethod
    def create_trip_report(title, description, location, date, difficulty, 
                          images=None, author_id=None):
        """
        Create a new trip report.
        
        Args:
            title (str): Trip report title
            description (str): Trip description
            location (str): Trip location
            date (str): Trip date in YYYY-MM-DD format
            difficulty (str): Trip difficulty level
            images (list): List of image objects (optional)
            author_id (int): Author user ID (optional, uses current user)
            
        Returns:
            tuple: (success: bool, message: str, trip_report: TripReport or None)
        """
        try:
            if not all([title, description, location, date]):
                return False, 'All required fields must be filled', None
            
            # Get author ID from session if not provided
            if author_id is None:
                author_id = session.get('user_id')
                if not author_id:
                    return False, 'User not authenticated', None
            
            # Parse date
            try:
                trip_date = datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                return False, 'Invalid date format', None
            
            # Create trip report
            new_trip_report = TripReport(
                title=title,
                description=description,
                location=location,
                date=trip_date.date(),
                difficulty=difficulty,
                images=images or [],
                author_id=author_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_trip_report)
            db.session.commit()
            
            logger.info(f"Trip report created: {title} by user {author_id}")
            return True, 'Trip report created successfully', new_trip_report
            
        except Exception as e:
            logger.error(f"Error creating trip report: {e}")
            db.session.rollback()
            return False, 'Failed to create trip report', None
    
    @staticmethod
    def get_trip_reports(page=1, per_page=6):
        """
        Get paginated trip reports.
        
        Args:
            page (int): Page number
            per_page (int): Items per page
            
        Returns:
            dict: Pagination data and trip reports
        """
        try:
            total = TripReport.query.count()
            trip_reports = TripReport.query.order_by(
                TripReport.created_at.desc()
            ).offset((page - 1) * per_page).limit(per_page).all()
            
            return {
                'trip_reports': trip_reports,
                'total': total,
                'page': page,
                'per_page': per_page,
                'has_prev': page > 1,
                'has_next': (page * per_page) < total,
                'prev_num': page - 1 if page > 1 else None,
                'next_num': page + 1 if (page * per_page) < total else None
            }
            
        except Exception as e:
            logger.error(f"Error getting trip reports: {e}")
            return {
                'trip_reports': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'has_prev': False,
                'has_next': False,
                'prev_num': None,
                'next_num': None
            }
    
    @staticmethod
    def get_trip_report(trip_id):
        """
        Get a specific trip report.
        
        Args:
            trip_id (int): Trip report ID
            
        Returns:
            TripReport or None: Trip report if found, None otherwise
        """
        try:
            return TripReport.query.get(trip_id)
        except Exception as e:
            logger.error(f"Error getting trip report {trip_id}: {e}")
            return None
    
    @staticmethod
    def delete_trip_report(trip_id, user_id=None, is_admin=False):
        """
        Delete a trip report.
        
        Args:
            trip_id (int): Trip report ID
            user_id (int): User ID (optional, uses current user)
            is_admin (bool): Whether user is admin (optional, uses session)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            trip_report = TripReport.query.get(trip_id)
            if not trip_report:
                return False, 'Trip report not found'
            
            # Get user info from session if not provided
            if user_id is None:
                user_id = session.get('user_id')
            if is_admin is False:
                is_admin = session.get('is_admin', False)
            
            # Check permissions
            if trip_report.author_id != user_id and not is_admin:
                return False, 'You can only delete your own trip reports'
            
            # Delete trip report
            db.session.delete(trip_report)
            db.session.commit()
            
            logger.info(f"Trip report deleted: {trip_report.title} by user {user_id}")
            return True, 'Trip report deleted successfully'
            
        except Exception as e:
            logger.error(f"Error deleting trip report {trip_id}: {e}")
            db.session.rollback()
            return False, 'Failed to delete trip report'
    
    @staticmethod
    def create_planned_trip(title, description, location, trip_date, difficulty,
                           max_participants, meeting_point, meeting_time,
                           estimated_duration, price=0, organizer_id=None):
        """
        Create a new planned trip.
        
        Args:
            title (str): Trip title
            description (str): Trip description
            location (str): Trip location
            trip_date (str): Trip date in YYYY-MM-DD format
            difficulty (str): Trip difficulty
            max_participants (int): Maximum number of participants
            meeting_point (str): Meeting point
            meeting_time (str): Meeting time in HH:MM format
            estimated_duration (str): Estimated duration
            price (float): Trip price (optional)
            organizer_id (int): Organizer user ID (optional, uses current user)
            
        Returns:
            tuple: (success: bool, message: str, planned_trip: PlannedTrip or None)
        """
        try:
            if not all([title, description, location, trip_date, meeting_point]):
                return False, 'All required fields must be filled', None
            
            # Get organizer ID from session if not provided
            if organizer_id is None:
                organizer_id = session.get('user_id')
                if not organizer_id:
                    return False, 'User not authenticated', None
            
            # Parse date and time
            try:
                trip_datetime = datetime.strptime(
                    f"{trip_date} {meeting_time or '09:00'}", 
                    '%Y-%m-%d %H:%M'
                )
            except ValueError:
                return False, 'Invalid date or time format', None
            
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
                organizer_id=organizer_id,
                status='open',
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_trip)
            db.session.commit()
            
            logger.info(f"Planned trip created: {title} by user {organizer_id}")
            return True, 'Planned trip created successfully', new_trip
            
        except Exception as e:
            logger.error(f"Error creating planned trip: {e}")
            db.session.rollback()
            return False, 'Failed to create planned trip', None
    
    @staticmethod
    def get_planned_trips():
        """
        Get upcoming and past planned trips.
        
        Returns:
            dict: Upcoming and past planned trips
        """
        try:
            current_date = datetime.utcnow()
            
            upcoming_trips = PlannedTrip.query.filter(
                PlannedTrip.trip_date >= current_date
            ).order_by(PlannedTrip.trip_date.asc()).all()
            
            past_trips = PlannedTrip.query.filter(
                PlannedTrip.trip_date < current_date
            ).order_by(PlannedTrip.trip_date.desc()).limit(10).all()
            
            return {
                'upcoming_trips': upcoming_trips,
                'past_trips': past_trips
            }
            
        except Exception as e:
            logger.error(f"Error getting planned trips: {e}")
            return {
                'upcoming_trips': [],
                'past_trips': []
            }
    
    @staticmethod
    def get_planned_trip(trip_id):
        """
        Get a specific planned trip.
        
        Args:
            trip_id (int): Planned trip ID
            
        Returns:
            PlannedTrip or None: Planned trip if found, None otherwise
        """
        try:
            return PlannedTrip.query.get(trip_id)
        except Exception as e:
            logger.error(f"Error getting planned trip {trip_id}: {e}")
            return None
    
    @staticmethod
    def register_for_trip(trip_id, user_id=None, phone='', 
                         emergency_contact='', notes=''):
        """
        Register a user for a planned trip.
        
        Args:
            trip_id (int): Planned trip ID
            user_id (int): User ID (optional, uses current user)
            phone (str): Phone number (optional)
            emergency_contact (str): Emergency contact (optional)
            notes (str): Additional notes (optional)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            trip = PlannedTrip.query.get(trip_id)
            if not trip:
                return False, 'Trip not found'
            
            # Get user ID from session if not provided
            if user_id is None:
                user_id = session.get('user_id')
                if not user_id:
                    return False, 'User not authenticated'
            
            # Check if already registered
            if any(p.user_id == user_id for p in trip.participants):
                return False, 'Already registered for this trip'
            
            # Check if trip is full
            if trip.max_participants and len(trip.participants) >= trip.max_participants:
                return False, 'Trip is full'
            
            # Check if trip date has passed
            if trip.trip_date < datetime.utcnow():
                return False, 'Cannot register for past trips'
            
            # Register user
            participant = TripParticipant(
                user_id=user_id,
                trip_id=trip_id,
                phone=phone,
                emergency_contact=emergency_contact,
                notes=notes,
                registered_at=datetime.utcnow()
            )
            
            db.session.add(participant)
            db.session.commit()
            
            logger.info(f"User {user_id} registered for trip: {trip.title}")
            return True, 'Successfully registered for trip'
            
        except Exception as e:
            logger.error(f"Error registering for trip {trip_id}: {e}")
            db.session.rollback()
            return False, 'Failed to register for trip'
    
    @staticmethod
    def unregister_from_trip(trip_id, user_id=None):
        """
        Unregister a user from a planned trip.
        
        Args:
            trip_id (int): Planned trip ID
            user_id (int): User ID (optional, uses current user)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            trip = PlannedTrip.query.get(trip_id)
            if not trip:
                return False, 'Trip not found'
            
            # Get user ID from session if not provided
            if user_id is None:
                user_id = session.get('user_id')
                if not user_id:
                    return False, 'User not authenticated'
            
            # Check if trip date has passed
            if trip.trip_date < datetime.utcnow():
                return False, 'Cannot unregister from past trips'
            
            # Remove user from participants
            participant = TripParticipant.query.filter_by(
                trip_id=trip_id,
                user_id=user_id
            ).first()
            
            if not participant:
                return False, 'Not registered for this trip'
            
            db.session.delete(participant)
            db.session.commit()
            
            logger.info(f"User {user_id} unregistered from trip: {trip.title}")
            return True, 'Successfully unregistered from trip'
            
        except Exception as e:
            logger.error(f"Error unregistering from trip {trip_id}: {e}")
            db.session.rollback()
            return False, 'Failed to unregister from trip'
    
    @staticmethod
    def update_gear_list(trip_id, gear_items):
        """
        Update gear list for a planned trip.
        
        Args:
            trip_id (int): Planned trip ID
            gear_items (str): Gear items as newline-separated string
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            trip = PlannedTrip.query.get(trip_id)
            if not trip:
                return False, 'Trip not found'
            
            # Parse gear items
            gear_list = [item.strip() for item in gear_items.split('\n') if item.strip()]
            
            trip.gear_list = gear_list
            db.session.commit()
            
            logger.info(f"Gear list updated for trip: {trip.title}")
            return True, 'Gear list updated successfully'
            
        except Exception as e:
            logger.error(f"Error updating gear list for trip {trip_id}: {e}")
            db.session.rollback()
            return False, 'Failed to update gear list'