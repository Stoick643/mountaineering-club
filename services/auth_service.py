"""
Authentication service for user management and authentication.
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, flash
import logging

from models import db, User

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication and user management."""
    
    @staticmethod
    def register_user(email, password, full_name, profile_picture=None):
        """
        Register a new user.
        
        Args:
            email (str): User's email address
            password (str): User's password
            full_name (str): User's full name
            profile_picture (str): URL to profile picture (optional)
            
        Returns:
            tuple: (success: bool, message: str, user: User or None)
        """
        try:
            # Check if user already exists
            if User.query.filter_by(email=email).first():
                return False, 'Email already registered', None
            
            # Split full name into first and last name
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Create new user (pending approval)
            new_user = User(
                email=email,
                password_hash=generate_password_hash(password) if password else '',
                first_name=first_name,
                last_name=last_name,
                profile_picture=profile_picture,
                is_approved=False,
                is_admin=False,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            logger.info(f"New user registered: {email}")
            return True, 'Registration successful! Please wait for admin approval.', new_user
            
        except Exception as e:
            logger.error(f"Error registering user {email}: {e}")
            db.session.rollback()
            return False, 'Registration failed. Please try again.', None
    
    @staticmethod
    def login_user(email, password):
        """
        Authenticate user login.
        
        Args:
            email (str): User's email address
            password (str): User's password
            
        Returns:
            tuple: (success: bool, message: str, user: User or None)
        """
        try:
            user = User.query.filter_by(email=email).first()
            
            if not user:
                return False, 'Invalid credentials', None
                
            if not check_password_hash(user.password_hash, password):
                return False, 'Invalid credentials', None
                
            if not user.is_approved:
                return False, 'Account pending approval', None
            
            # Create session
            session['user_id'] = user.id
            session['user_name'] = user.full_name
            session['is_admin'] = user.is_admin
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"User logged in: {email}")
            return True, 'Login successful', user
            
        except Exception as e:
            logger.error(f"Error logging in user {email}: {e}")
            return False, 'Login failed. Please try again.', None
    
    @staticmethod
    def logout_user():
        """
        Log out the current user.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            user_name = session.get('user_name', 'Unknown')
            session.clear()
            logger.info(f"User logged out: {user_name}")
            return True, 'Logged out successfully'
            
        except Exception as e:
            logger.error(f"Error logging out user: {e}")
            return False, 'Logout failed'
    
    @staticmethod
    def get_current_user():
        """
        Get the current authenticated user.
        
        Returns:
            User or None: Current user if authenticated, None otherwise
        """
        user_id = session.get('user_id')
        if user_id:
            return User.query.get(user_id)
        return None
    
    @staticmethod
    def is_authenticated():
        """
        Check if user is authenticated.
        
        Returns:
            bool: True if user is authenticated, False otherwise
        """
        return 'user_id' in session
    
    @staticmethod
    def is_admin():
        """
        Check if current user is an admin.
        
        Returns:
            bool: True if user is admin, False otherwise
        """
        return session.get('is_admin', False)
    
    @staticmethod
    def oauth_login(provider, user_info):
        """
        Handle OAuth login (Google, Facebook, etc.).
        
        Args:
            provider (str): OAuth provider name
            user_info (dict): User information from OAuth provider
            
        Returns:
            tuple: (success: bool, message: str, user: User or None)
        """
        try:
            email = user_info.get('email')
            full_name = user_info.get('name', '')
            profile_picture = user_info.get('picture')
            
            if not email:
                return False, 'Could not retrieve email address', None
            
            # Check if user exists
            user = User.query.filter_by(email=email).first()
            
            if user:
                # User exists - log them in
                if not user.is_approved:
                    return False, 'Your account is pending admin approval', None
                
                # Update profile picture if available
                if profile_picture and not user.profile_picture:
                    user.profile_picture = profile_picture
                    db.session.commit()
                
                # Create session
                session['user_id'] = user.id
                session['user_name'] = user.full_name
                session['is_admin'] = user.is_admin
                
                # Update last login
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"User logged in via {provider}: {email}")
                return True, f'Successfully logged in via {provider.title()}', user
            
            else:
                # Create new user account (pending approval)
                success, message, new_user = AuthService.register_user(
                    email=email,
                    password='',  # OAuth users don't have passwords
                    full_name=full_name,
                    profile_picture=profile_picture
                )
                
                if success:
                    logger.info(f"New OAuth user registered via {provider}: {email}")
                    return True, f'Account created via {provider.title()}! Please wait for admin approval.', new_user
                else:
                    return False, message, None
                    
        except Exception as e:
            logger.error(f"OAuth {provider} error: {e}")
            db.session.rollback()
            return False, 'Login failed. Please try again.', None