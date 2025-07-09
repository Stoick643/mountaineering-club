"""
Authentication routes (login, register, OAuth).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from authlib.integrations.flask_client import OAuth
import logging

from services.auth_service import AuthService

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        success, message, user = AuthService.register_user(email, password, full_name)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'error')
    
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        success, message, user = AuthService.login_user(email, password)
        
        if success:
            return redirect(url_for('main.dashboard'))
        else:
            flash(message, 'error')
    
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """User logout."""
    success, message = AuthService.logout_user()
    flash(message, 'success' if success else 'error')
    return redirect(url_for('main.home'))


@auth_bp.route('/auth/<provider>')
def oauth_login(provider):
    """OAuth login initiation."""
    try:
        oauth = OAuth()
        
        if provider == 'google':
            google = oauth.create_client('google')
            redirect_uri = url_for('auth.oauth_callback', provider='google', _external=True)
            return google.authorize_redirect(redirect_uri)
        elif provider == 'facebook':
            facebook = oauth.create_client('facebook')
            redirect_uri = url_for('auth.oauth_callback', provider='facebook', _external=True)
            return facebook.authorize_redirect(redirect_uri)
        else:
            flash('Unsupported login provider', 'error')
            return redirect(url_for('auth.login'))
    except Exception as e:
        logger.error(f"OAuth initiation error: {e}")
        flash('Login failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/auth/<provider>/callback')
def oauth_callback(provider):
    """OAuth callback handler."""
    try:
        oauth = OAuth()
        
        if provider == 'google':
            google = oauth.create_client('google')
            token = google.authorize_access_token()
            user_info = token.get('userinfo')
            if user_info:
                user_data = {
                    'email': user_info['email'],
                    'name': user_info['name'],
                    'picture': user_info.get('picture')
                }
        elif provider == 'facebook':
            facebook = oauth.create_client('facebook')
            token = facebook.authorize_access_token()
            resp = facebook.get('me?fields=id,name,email,picture', token=token)
            user_info = resp.json()
            user_data = {
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'picture': user_info.get('picture', {}).get('data', {}).get('url')
            }
        else:
            flash('Unsupported login provider', 'error')
            return redirect(url_for('auth.login'))
        
        success, message, user = AuthService.oauth_login(provider, user_data)
        
        if success:
            flash(message, 'success')
            if user and user.is_approved:
                return redirect(url_for('main.dashboard'))
            else:
                return redirect(url_for('auth.login'))
        else:
            flash(message, 'error')
            return redirect(url_for('auth.login'))
    
    except Exception as e:
        logger.error(f"OAuth {provider} callback error: {e}")
        flash('Login failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))