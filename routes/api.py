"""
API routes for AJAX requests and external integrations.
"""
from flask import Blueprint, jsonify, request
import logging

from services.news_service import NewsService
from services.admin_service import AdminService
from utils.decorators import login_required, admin_required
from utils.helpers import success_response, error_response

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Initialize news service
news_service = NewsService()


# Historical Events API
@api_bp.route('/today-in-history')
@login_required
def today_in_history():
    """Get historical event for today."""
    try:
        event = news_service.get_today_historical_event()
        
        if event:
            return success_response({'event': event})
        else:
            return error_response('No event found for today', 404)
            
    except Exception as e:
        logger.error(f"Error fetching today's historical event: {e}")
        return error_response('Error retrieving event', 500)


@api_bp.route('/history/<date>')
@login_required  
def history_by_date(date):
    """Get historical event for specific date (MM-DD format)."""
    try:
        # Validate date format
        import re
        if not re.match(r'^\d{2}-\d{2}$', date):
            return error_response('Invalid date format (use MM-DD)', 400)
        
        event = news_service.get_today_historical_event(date)
        
        if event:
            return success_response({'event': event})
        else:
            return error_response(f'No event found for date {date}', 404)
            
    except Exception as e:
        logger.error(f"Error fetching historical event for {date}: {e}")
        return error_response('Error retrieving event', 500)


@api_bp.route('/history/random')
@login_required
def random_history():
    """Get random historical event."""
    try:
        event = news_service.get_random_historical_event()
        
        if event:
            return success_response({'event': event})
        else:
            return error_response('No random event available', 404)
            
    except Exception as e:
        logger.error(f"Error fetching random historical event: {e}")
        return error_response('Error retrieving event', 500)


@api_bp.route('/history/featured')
@login_required
def featured_history():
    """Get featured historical events."""
    try:
        events = news_service.get_featured_historical_events(limit=5)
        
        return success_response({
            'events': events,
            'count': len(events)
        })
        
    except Exception as e:
        logger.error(f"Error fetching featured historical events: {e}")
        return error_response('Error retrieving events', 500)


@api_bp.route('/history/category/<category>')
@login_required
def historical_events_by_category(category):
    """Get historical events by category."""
    try:
        limit = request.args.get('limit', 10, type=int)
        events = news_service.get_historical_events_by_category(category, limit)
        
        return success_response({
            'events': events,
            'category': category
        })
        
    except Exception as e:
        logger.error(f"Error getting events by category {category}: {e}")
        return error_response('Error retrieving events', 500)


@api_bp.route('/history/search')
@login_required
def search_historical_events():
    """Search historical events."""
    try:
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return error_response('Search query is required', 400)
        
        events = news_service.search_historical_events(query, limit)
        
        return success_response({
            'events': events,
            'query': query
        })
        
    except Exception as e:
        logger.error(f"Error searching historical events: {e}")
        return error_response('Search failed', 500)


# News API
@api_bp.route('/news/latest')
@login_required
def get_latest_news():
    """Get latest curated news articles."""
    try:
        limit = request.args.get('limit', 5, type=int)
        category = request.args.get('category')
        
        articles = news_service.get_latest_news(limit=limit, category=category)
        
        return success_response({'articles': articles})
        
    except Exception as e:
        logger.error(f"Error getting latest news: {e}")
        return error_response('Error loading news', 500)


@api_bp.route('/news/category/<category>')
@login_required
def get_news_by_category(category):
    """Get news articles by category."""
    try:
        limit = request.args.get('limit', 5, type=int)
        
        articles = news_service.get_latest_news(limit=limit, category=category)
        
        return success_response({
            'articles': articles,
            'category': category
        })
        
    except Exception as e:
        logger.error(f"Error getting news by category {category}: {e}")
        return error_response('Error loading news', 500)


@api_bp.route('/news/categories')
@login_required
def get_news_by_categories():
    """Get news grouped by all categories."""
    try:
        articles_by_category = news_service.get_news_by_category()
        
        return success_response({'categories': articles_by_category})
        
    except Exception as e:
        logger.error(f"Error getting news by categories: {e}")
        return error_response('Error loading news', 500)


# Admin API routes
@api_bp.route('/admin/news/update', methods=['POST'])
@admin_required
def update_news_feed():
    """Manually trigger news update (admin only)."""
    try:
        success, message, stats = news_service.update_news_feed()
        
        if success:
            return success_response({
                'message': message,
                'stats': stats
            })
        else:
            return error_response(message, 500)
        
    except Exception as e:
        logger.error(f"Error updating news feed: {e}")
        return error_response('Error updating news feed', 500)


@api_bp.route('/admin/news/stats')
@admin_required
def get_news_stats():
    """Get news curation statistics (admin only)."""
    try:
        stats = news_service.get_news_statistics()
        
        return success_response({'stats': stats})
        
    except Exception as e:
        logger.error(f"Error getting news stats: {e}")
        return error_response('Error getting statistics', 500)


@api_bp.route('/admin/historical-events/<int:event_id>/verify', methods=['POST'])
@admin_required
def verify_historical_event(event_id):
    """Mark historical event as verified (admin only)."""
    try:
        success, message = news_service.verify_historical_event(event_id)
        
        if success:
            return success_response(message=message)
        else:
            return error_response(message, 404)
            
    except Exception as e:
        logger.error(f"Error verifying event {event_id}: {e}")
        return error_response('Error verifying event', 500)


@api_bp.route('/admin/historical-events/<int:event_id>/feature', methods=['POST'])
@admin_required
def feature_historical_event(event_id):
    """Mark historical event as featured (admin only)."""
    try:
        success, message = news_service.feature_historical_event(event_id)
        
        if success:
            return success_response(message=message)
        else:
            return error_response(message, 404)
            
    except Exception as e:
        logger.error(f"Error featuring event {event_id}: {e}")
        return error_response('Error featuring event', 500)


@api_bp.route('/admin/historical-events/generate-range', methods=['POST'])
@admin_required
def generate_historical_events_range():
    """Generate historical events for date range (admin only)."""
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            return error_response('start_date and end_date required', 400)
        
        success, message, count = news_service.generate_historical_events_range(start_date, end_date)
        
        if success:
            return success_response({
                'message': message,
                'generated_count': count
            })
        else:
            return error_response(message, 500)
        
    except Exception as e:
        logger.error(f"Error generating event range: {e}")
        return error_response('Error generating events', 500)


@api_bp.route('/admin/historical-events/stats')
@admin_required
def get_historical_events_stats():
    """Get statistics about historical events (admin only)."""
    try:
        stats = news_service.get_historical_events_statistics()
        
        return success_response({'stats': stats})
        
    except Exception as e:
        logger.error(f"Error getting historical events stats: {e}")
        return error_response('Error getting statistics', 500)


# Comments API (consolidated from admin routes)
@api_bp.route('/comments/<content_type>/<content_id>')
@login_required
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
        
        return success_response({'comments': comments_data})
    
    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        return error_response('Error fetching comments', 500)


@api_bp.route('/comments/<content_type>/<content_id>', methods=['POST'])
@login_required
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
            return success_response({'comment': comment_data})
        else:
            return error_response(message, 400)
    
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        return error_response('Error adding comment', 500)


@api_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Delete a comment (only by author or admin)."""
    try:
        success, message = AdminService.delete_comment(comment_id)
        
        if success:
            return success_response(message=message)
        else:
            return error_response(message, 400)
    
    except Exception as e:
        logger.error(f"Error deleting comment: {e}")
        return error_response('Error deleting comment', 500)