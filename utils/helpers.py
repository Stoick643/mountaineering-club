"""
Helper functions for the application.
"""
from datetime import datetime
from flask import jsonify
import logging

logger = logging.getLogger(__name__)


def format_datetime(dt):
    """Format datetime for display."""
    if not dt:
        return ''
    if hasattr(dt, 'strftime'):
        return dt.strftime('%d.%m.%Y ob %H:%M')
    return str(dt)


def handle_error(error_msg, status_code=500):
    """Handle errors consistently."""
    logger.error(error_msg)
    return jsonify({'error': error_msg}), status_code


def success_response(data=None, message='Success'):
    """Create success response."""
    response = {'success': True, 'message': message}
    if data:
        response.update(data)
    return jsonify(response)


def error_response(message='Error', status_code=400):
    """Create error response."""
    return jsonify({'success': False, 'error': message}), status_code