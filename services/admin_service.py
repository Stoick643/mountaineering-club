"""
Admin service for administrative functions.
"""
from datetime import datetime
from flask import session
import logging

from models import db, User, Announcement, Comment

logger = logging.getLogger(__name__)


class AdminService:
    """Service for handling administrative functions."""
    
    @staticmethod
    def get_user_management_data():
        """
        Get data for user management dashboard.
        
        Returns:
            dict: User management data including stats and user lists
        """
        try:
            pending_users = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).all()
            all_users = User.query.order_by(User.created_at.desc()).all()
            
            stats = {
                'total_users': User.query.count(),
                'pending_approval': User.query.filter_by(is_approved=False).count(),
                'approved_users': User.query.filter_by(is_approved=True).count(),
                'admin_users': User.query.filter_by(is_admin=True).count()
            }
            
            return {
                'pending_users': pending_users,
                'all_users': all_users,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Error getting user management data: {e}")
            return {
                'pending_users': [],
                'all_users': [],
                'stats': {
                    'total_users': 0,
                    'pending_approval': 0,
                    'approved_users': 0,
                    'admin_users': 0
                }
            }
    
    @staticmethod
    def approve_user(user_id, admin_id=None):
        """
        Approve a user account.
        
        Args:
            user_id (int): User ID to approve
            admin_id (int): Admin user ID (optional, uses current user)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            user = User.query.get(int(user_id))
            if not user:
                return False, 'User not found'
            
            # Get admin info from session if not provided
            if admin_id is None:
                admin_id = session.get('user_id')
                admin_name = session.get('user_name', 'Unknown')
            else:
                admin_user = User.query.get(admin_id)
                admin_name = admin_user.full_name if admin_user else 'Unknown'
            
            user.is_approved = True
            db.session.commit()
            
            logger.info(f"Admin {admin_name} approved user {user.email}")
            return True, f'User {user.full_name} approved successfully'
            
        except Exception as e:
            logger.error(f"Error approving user {user_id}: {e}")
            db.session.rollback()
            return False, 'Error approving user'
    
    @staticmethod
    def reject_user(user_id, admin_id=None):
        """
        Reject and remove a user account.
        
        Args:
            user_id (int): User ID to reject
            admin_id (int): Admin user ID (optional, uses current user)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, 'User not found'
            
            # Get admin info from session if not provided
            if admin_id is None:
                admin_id = session.get('user_id')
                admin_name = session.get('user_name', 'Unknown')
            else:
                admin_user = User.query.get(admin_id)
                admin_name = admin_user.full_name if admin_user else 'Unknown'
            
            user_name = user.full_name
            user_email = user.email
            
            db.session.delete(user)
            db.session.commit()
            
            logger.info(f"Admin {admin_name} rejected user {user_email}")
            return True, f'User {user_name} rejected and removed'
            
        except Exception as e:
            logger.error(f"Error rejecting user {user_id}: {e}")
            db.session.rollback()
            return False, 'Error rejecting user'
    
    @staticmethod
    def toggle_admin_status(user_id, admin_id=None):
        """
        Toggle admin status for a user.
        
        Args:
            user_id (int): User ID to toggle admin status
            admin_id (int): Admin user ID (optional, uses current user)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, 'User not found'
            
            # Get admin info from session if not provided
            if admin_id is None:
                admin_id = session.get('user_id')
                admin_name = session.get('user_name', 'Unknown')
            else:
                admin_user = User.query.get(admin_id)
                admin_name = admin_user.full_name if admin_user else 'Unknown'
            
            new_admin_status = not user.is_admin
            user.is_admin = new_admin_status
            db.session.commit()
            
            action = 'promoted to' if new_admin_status else 'removed from'
            logger.info(f"Admin {admin_name} changed admin status for {user.email}")
            return True, f'{user.full_name} {action} admin'
            
        except Exception as e:
            logger.error(f"Error toggling admin for {user_id}: {e}")
            db.session.rollback()
            return False, 'Error updating admin status'
    
    @staticmethod
    def get_announcements():
        """
        Get all announcements for admin management.
        
        Returns:
            list: List of announcements
        """
        try:
            return Announcement.query.order_by(Announcement.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting announcements: {e}")
            return []
    
    @staticmethod
    def create_announcement(title, content, author_id=None):
        """
        Create a new announcement.
        
        Args:
            title (str): Announcement title
            content (str): Announcement content
            author_id (int): Author user ID (optional, uses current user)
            
        Returns:
            tuple: (success: bool, message: str, announcement: Announcement or None)
        """
        try:
            if not title or not content:
                return False, 'Title and content are required', None
            
            # Get author ID from session if not provided
            if author_id is None:
                author_id = session.get('user_id')
                if not author_id:
                    return False, 'User not authenticated', None
            
            new_announcement = Announcement(
                title=title,
                content=content,
                author_id=author_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_announcement)
            db.session.commit()
            
            author_name = session.get('user_name', 'Unknown')
            logger.info(f"Admin {author_name} created announcement: {title}")
            return True, 'Announcement created successfully', new_announcement
            
        except Exception as e:
            logger.error(f"Error creating announcement: {e}")
            db.session.rollback()
            return False, 'Failed to create announcement', None
    
    @staticmethod
    def delete_announcement(announcement_id, admin_id=None):
        """
        Delete an announcement.
        
        Args:
            announcement_id (int): Announcement ID to delete
            admin_id (int): Admin user ID (optional, uses current user)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            announcement = Announcement.query.get(announcement_id)
            if not announcement:
                return False, 'Announcement not found'
            
            # Get admin info from session if not provided
            if admin_id is None:
                admin_name = session.get('user_name', 'Unknown')
            else:
                admin_user = User.query.get(admin_id)
                admin_name = admin_user.full_name if admin_user else 'Unknown'
            
            announcement_title = announcement.title
            db.session.delete(announcement)
            db.session.commit()
            
            logger.info(f"Admin {admin_name} deleted announcement: {announcement_title}")
            return True, 'Announcement deleted successfully'
            
        except Exception as e:
            logger.error(f"Error deleting announcement {announcement_id}: {e}")
            db.session.rollback()
            return False, 'Error deleting announcement'
    
    @staticmethod
    def get_comments(content_type, content_id):
        """
        Get comments for announcements or trip reports.
        
        Args:
            content_type (str): Type of content ('announcement' or 'trip_report')
            content_id (int): Content ID
            
        Returns:
            list: List of comments
        """
        try:
            if content_type not in ['announcement', 'trip_report']:
                return []
            
            if content_type == 'announcement':
                comments = Comment.query.filter_by(announcement_id=int(content_id)).order_by(Comment.created_at.asc()).all()
            else:  # trip_report
                comments = Comment.query.filter_by(trip_report_id=int(content_id)).order_by(Comment.created_at.asc()).all()
            
            return comments
            
        except Exception as e:
            logger.error(f"Error getting comments: {e}")
            return []
    
    @staticmethod
    def add_comment(content_type, content_id, comment_text, author_id=None):
        """
        Add a comment to announcements or trip reports.
        
        Args:
            content_type (str): Type of content ('announcement' or 'trip_report')
            content_id (int): Content ID
            comment_text (str): Comment text
            author_id (int): Author user ID (optional, uses current user)
            
        Returns:
            tuple: (success: bool, message: str, comment: Comment or None)
        """
        try:
            if content_type not in ['announcement', 'trip_report']:
                return False, 'Invalid content type', None
            
            comment_text = comment_text.strip()
            if not comment_text:
                return False, 'Comment cannot be empty', None
            
            if len(comment_text) > 1000:
                return False, 'Comment too long (max 1000 characters)', None
            
            # Get author ID from session if not provided
            if author_id is None:
                author_id = session.get('user_id')
                if not author_id:
                    return False, 'User not authenticated', None
            
            # Verify the content exists
            if content_type == 'announcement':
                from models import Announcement
                content = Announcement.query.get(int(content_id))
            else:  # trip_report
                from models import TripReport
                content = TripReport.query.get(int(content_id))
            
            if not content:
                return False, 'Content not found', None
            
            # Create new comment
            new_comment = Comment(
                content=comment_text,
                author_id=author_id,
                announcement_id=int(content_id) if content_type == 'announcement' else None,
                trip_report_id=int(content_id) if content_type == 'trip_report' else None,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_comment)
            db.session.commit()
            
            author_name = session.get('user_name', 'Unknown')
            logger.info(f"User {author_name} added comment to {content_type} {content_id}")
            return True, 'Comment added successfully', new_comment
            
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            db.session.rollback()
            return False, 'Error adding comment', None
    
    @staticmethod
    def delete_comment(comment_id, user_id=None, is_admin=False):
        """
        Delete a comment (only by author or admin).
        
        Args:
            comment_id (int): Comment ID to delete
            user_id (int): User ID (optional, uses current user)
            is_admin (bool): Whether user is admin (optional, uses session)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            comment = Comment.query.get(comment_id)
            if not comment:
                return False, 'Comment not found'
            
            # Get user info from session if not provided
            if user_id is None:
                user_id = session.get('user_id')
            if is_admin is False:
                is_admin = session.get('is_admin', False)
            
            # Check permissions
            if comment.author_id != user_id and not is_admin:
                return False, 'Not authorized to delete this comment'
            
            db.session.delete(comment)
            db.session.commit()
            
            user_name = session.get('user_name', 'Unknown')
            logger.info(f"User {user_name} deleted comment {comment_id}")
            return True, 'Comment deleted successfully'
            
        except Exception as e:
            logger.error(f"Error deleting comment: {e}")
            db.session.rollback()
            return False, 'Error deleting comment'