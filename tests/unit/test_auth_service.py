"""
Unit tests for AuthService.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User
from services.auth_service import AuthService


@pytest.mark.unit
class TestAuthService:
    """Test cases for AuthService."""
    
    def test_register_user_success(self, app):
        """Test successful user registration."""
        with app.app_context():
            success, message, user = AuthService.register_user(
                email='test@example.com',
                password='password123',
                full_name='Test User'
            )
            
            assert success is True
            assert 'Registration successful' in message
            assert user is not None
            assert user.email == 'test@example.com'
            assert user.first_name == 'Test'
            assert user.last_name == 'User'
            assert user.is_approved is False
            assert user.is_admin is False
    
    def test_register_user_existing_email(self, app, sample_user):
        """Test registration with existing email."""
        with app.app_context():
            # Add existing user
            db.session.add(sample_user)
            db.session.commit()
            
            success, message, user = AuthService.register_user(
                email=sample_user.email,
                password='password123',
                full_name='Another User'
            )
            
            assert success is False
            assert 'Email already registered' in message
            assert user is None
    
    def test_register_user_single_name(self, app):
        """Test registration with single name."""
        with app.app_context():
            success, message, user = AuthService.register_user(
                email='test@example.com',
                password='password123',
                full_name='TestUser'
            )
            
            assert success is True
            assert user.first_name == 'TestUser'
            assert user.last_name == ''
    
    def test_login_user_success(self, app, sample_user):
        """Test successful user login."""
        with app.app_context():
            # Add approved user
            db.session.add(sample_user)
            db.session.commit()
            
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    success, message, user = AuthService.login_user(
                        email=sample_user.email,
                        password='password123'
                    )
                    
                    assert success is True
                    assert 'Login successful' in message
                    assert user is not None
                    assert user.email == sample_user.email
    
    def test_login_user_invalid_email(self, app):
        """Test login with invalid email."""
        with app.app_context():
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    success, message, user = AuthService.login_user(
                        email='nonexistent@example.com',
                        password='password123'
                    )
                    
                    assert success is False
                    assert 'Invalid credentials' in message
                    assert user is None
    
    def test_login_user_invalid_password(self, app, sample_user):
        """Test login with invalid password."""
        with app.app_context():
            db.session.add(sample_user)
            db.session.commit()
            
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    success, message, user = AuthService.login_user(
                        email=sample_user.email,
                        password='wrongpassword'
                    )
                    
                    assert success is False
                    assert 'Invalid credentials' in message
                    assert user is None
    
    def test_login_user_not_approved(self, app):
        """Test login with unapproved user."""
        with app.app_context():
            unapproved_user = User(
                email='unapproved@example.com',
                password_hash=generate_password_hash('password123'),
                first_name='Unapproved',
                last_name='User',
                is_approved=False,
                is_admin=False
            )
            db.session.add(unapproved_user)
            db.session.commit()
            
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    success, message, user = AuthService.login_user(
                        email=unapproved_user.email,
                        password='password123'
                    )
                    
                    assert success is False
                    assert 'Account pending approval' in message
                    assert user is None
    
    def test_logout_user(self, app):
        """Test user logout."""
        with app.app_context():
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    # Set up session
                    sess['user_id'] = 1
                    sess['user_name'] = 'Test User'
                    sess['is_admin'] = False
                    
                    success, message = AuthService.logout_user()
                    
                    assert success is True
                    assert 'Logged out successfully' in message
    
    def test_is_authenticated_true(self, app):
        """Test is_authenticated with authenticated user."""
        with app.app_context():
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = 1
                    
                    assert AuthService.is_authenticated() is True
    
    def test_is_authenticated_false(self, app):
        """Test is_authenticated with no user."""
        with app.app_context():
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    assert AuthService.is_authenticated() is False
    
    def test_is_admin_true(self, app):
        """Test is_admin with admin user."""
        with app.app_context():
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = 1
                    sess['is_admin'] = True
                    
                    assert AuthService.is_admin() is True
    
    def test_is_admin_false(self, app):
        """Test is_admin with regular user."""
        with app.app_context():
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = 1
                    sess['is_admin'] = False
                    
                    assert AuthService.is_admin() is False
    
    def test_get_current_user(self, app, sample_user):
        """Test get_current_user with authenticated user."""
        with app.app_context():
            db.session.add(sample_user)
            db.session.commit()
            
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = sample_user.id
                    
                    user = AuthService.get_current_user()
                    
                    assert user is not None
                    assert user.email == sample_user.email
    
    def test_get_current_user_none(self, app):
        """Test get_current_user with no authenticated user."""
        with app.app_context():
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    user = AuthService.get_current_user()
                    
                    assert user is None
    
    def test_oauth_login_existing_user(self, app, sample_user):
        """Test OAuth login with existing user."""
        with app.app_context():
            db.session.add(sample_user)
            db.session.commit()
            
            user_info = {
                'email': sample_user.email,
                'name': sample_user.full_name,
                'picture': 'https://example.com/photo.jpg'
            }
            
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    success, message, user = AuthService.oauth_login('google', user_info)
                    
                    assert success is True
                    assert 'Successfully logged in' in message
                    assert user is not None
                    assert user.email == sample_user.email
    
    def test_oauth_login_new_user(self, app):
        """Test OAuth login with new user."""
        with app.app_context():
            user_info = {
                'email': 'newuser@example.com',
                'name': 'New User',
                'picture': 'https://example.com/photo.jpg'
            }
            
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    success, message, user = AuthService.oauth_login('google', user_info)
                    
                    assert success is True
                    assert 'Account created' in message
                    assert user is not None
                    assert user.email == 'newuser@example.com'
                    assert user.is_approved is False
    
    def test_oauth_login_no_email(self, app):
        """Test OAuth login without email."""
        with app.app_context():
            user_info = {
                'name': 'Test User'
            }
            
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    success, message, user = AuthService.oauth_login('google', user_info)
                    
                    assert success is False
                    assert 'Could not retrieve email' in message
                    assert user is None