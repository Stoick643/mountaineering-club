"""
Route modules for the mountaineering club application.
"""
from .main import main_bp
from .auth import auth_bp
from .admin import admin_bp
from .api import api_bp
from .trips import trips_bp

__all__ = [
    'main_bp',
    'auth_bp', 
    'admin_bp',
    'api_bp',
    'trips_bp'
]