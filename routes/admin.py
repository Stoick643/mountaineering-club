"""
Admin routes for user management and announcements.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import logging

from services.admin_service import AdminService
from utils.decorators import admin_required
from utils.helpers import handle_error, success_response, error_response

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@admin_required
def panel():
    """Admin panel with user management."""
    try:
        data = AdminService.get_user_management_data()
        return render_template('admin_panel.html', 
                             pending_users=data['pending_users'],
                             all_users=data['all_users'],
                             stats=data['stats'])
    except Exception as e:
        logger.error(f"Error loading admin panel: {e}")
        flash('Error loading admin panel', 'error')
        return redirect(url_for('main.dashboard'))


@admin_bp.route('/approve_user/<user_id>')
@admin_required
def approve_user(user_id):
    """Approve a user account."""
    success, message = AdminService.approve_user(user_id)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('admin.panel'))


@admin_bp.route('/reject_user/<int:user_id>')
@admin_required
def reject_user(user_id):
    """Reject and remove a user account."""
    success, message = AdminService.reject_user(user_id)
    flash(message, 'warning' if success else 'error')
    return redirect(url_for('admin.panel'))


@admin_bp.route('/toggle_admin/<int:user_id>')
@admin_required
def toggle_admin(user_id):
    """Toggle admin status for a user."""
    success, message = AdminService.toggle_admin_status(user_id)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('admin.panel'))


@admin_bp.route('/announcements')
@admin_required
def announcements():
    """Admin announcements management."""
    try:
        announcements = AdminService.get_announcements()
        return render_template('admin_announcements.html', announcements=announcements)
    except Exception as e:
        logger.error(f"Error loading announcements: {e}")
        flash('Error loading announcements', 'error')
        return redirect(url_for('admin.panel'))


@admin_bp.route('/announcements/create', methods=['GET', 'POST'])
@admin_required
def create_announcement():
    """Create a new announcement."""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        success, message, announcement = AdminService.create_announcement(title, content)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('admin.announcements'))
        else:
            flash(message, 'error')
    
    return render_template('create_announcement.html')


@admin_bp.route('/announcements/delete/<int:announcement_id>')
@admin_required
def delete_announcement(announcement_id):
    """Delete an announcement."""
    success, message = AdminService.delete_announcement(announcement_id)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('admin.announcements'))


# API routes for comments
@admin_bp.route('/api/comments/<content_type>/<content_id>')
@admin_required
def get_comments(content_type, content_id):
    """Get comments for announcements or trip reports."""
    try:
        comments = AdminService.get_comments(content_type, content_id)
        
        # Convert to JSON format
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'content': comment.content,
                'author_name': comment.author.full_name if comment.author else 'Unknown',
                'author_id': comment.author_id,
                'created_at': comment.created_at.isoformat() if hasattr(comment.created_at, 'isoformat') else str(comment.created_at)
            })
        
        return jsonify({'comments': comments_data})
    
    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        return error_response('Error fetching comments', 500)


@admin_bp.route('/api/comments/<content_type>/<content_id>', methods=['POST'])
@admin_required
def add_comment(content_type, content_id):
    """Add a comment to announcements or trip reports."""
    try:
        data = request.get_json()
        comment_text = data.get('comment', '').strip()
        
        success, message, comment = AdminService.add_comment(content_type, content_id, comment_text)
        
        if success:
            comment_data = {
                'id': comment.id,
                'content': comment.content,
                'author_name': comment.author.full_name,
                'author_id': comment.author_id,
                'created_at': comment.created_at.isoformat() if hasattr(comment.created_at, 'isoformat') else str(comment.created_at)
            }
            return jsonify({'comment': comment_data}), 201
        else:
            return error_response(message, 400)
    
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        return error_response('Error adding comment', 500)


@admin_bp.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@admin_required
def delete_comment(comment_id):
    """Delete a comment (admin only)."""
    try:
        success, message = AdminService.delete_comment(comment_id)
        
        if success:
            return success_response(message=message)
        else:
            return error_response(message, 400)
    
    except Exception as e:
        logger.error(f"Error deleting comment: {e}")
        return error_response('Error deleting comment', 500)