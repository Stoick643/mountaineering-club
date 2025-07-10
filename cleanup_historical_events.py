#!/usr/bin/env python3
"""
Historical Events Database Cleanup Script

This script allows you to delete stale historical events from the database
to force regeneration with updated prompts.

Usage:
    python cleanup_historical_events.py --date 07-10    # Delete specific date
    python cleanup_historical_events.py --all           # Delete all events
    python cleanup_historical_events.py --today         # Delete today's event
"""

import sys
import argparse
from datetime import datetime
from app import create_app
from models.historical_event import HistoricalEvent

def delete_event_by_date(date_str, force=False):
    """Delete historical event for specific date (MM-DD format)"""
    
    app, _ = create_app()
    
    with app.app_context():
        event = HistoricalEvent.query.filter_by(date=date_str).first()
        
        if event:
            print(f"Found event for {date_str}: {event.title}")
            print(f"Year: {event.year}")
            print(f"Description: {event.description[:100]}...")
            
            if force:
                confirm = 'y'
                print(f"\nForce deleting event...")
            else:
                confirm = input(f"\nDelete this event? (y/N): ").strip().lower()
            
            if confirm == 'y':
                try:
                    from models import db
                    db.session.delete(event)
                    db.session.commit()
                    print(f"✅ Successfully deleted event for {date_str}")
                    return True
                except Exception as e:
                    print(f"❌ Error deleting event: {e}")
                    db.session.rollback()
                    return False
            else:
                print("Operation cancelled.")
                return False
        else:
            print(f"No event found for date {date_str}")
            return False

def delete_all_events(force=False):
    """Delete all historical events"""
    
    app, _ = create_app()
    
    with app.app_context():
        count = HistoricalEvent.query.count()
        
        if count == 0:
            print("No historical events found in database.")
            return True
        
        print(f"Found {count} historical events in database.")
        
        if force:
            confirm = 'y'
            print("Force deleting all events...")
        else:
            confirm = input(f"Delete ALL {count} events? This cannot be undone! (y/N): ").strip().lower()
        
        if confirm == 'y':
            try:
                from models import db
                HistoricalEvent.query.delete()
                db.session.commit()
                print(f"✅ Successfully deleted all {count} historical events")
                return True
            except Exception as e:
                print(f"❌ Error deleting events: {e}")
                db.session.rollback()
                return False
        else:
            print("Operation cancelled.")
            return False

def list_events():
    """List all historical events in database"""
    
    app, _ = create_app()
    
    with app.app_context():
        events = HistoricalEvent.query.order_by(HistoricalEvent.date).all()
        
        if not events:
            print("No historical events found in database.")
            return
        
        print(f"\nFound {len(events)} historical events:")
        print("-" * 80)
        
        for event in events:
            print(f"Date: {event.date} | Year: {event.year} | {event.title}")
            print(f"  {event.description[:100]}...")
            print(f"  Created: {event.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print()

def main():
    parser = argparse.ArgumentParser(description='Cleanup historical events database')
    group = parser.add_mutually_exclusive_group(required=True)
    
    group.add_argument('--date', type=str, help='Delete event for specific date (MM-DD format, e.g., 07-10)')
    group.add_argument('--today', action='store_true', help='Delete event for today\'s date')
    group.add_argument('--all', action='store_true', help='Delete ALL historical events')
    group.add_argument('--list', action='store_true', help='List all historical events')
    
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    if args.list:
        list_events()
    elif args.today:
        today_date = datetime.now().strftime("%m-%d")
        print(f"Deleting event for today's date: {today_date}")
        delete_event_by_date(today_date, force=args.force)
    elif args.date:
        # Validate date format
        try:
            datetime.strptime(args.date, "%m-%d")
        except ValueError:
            print("❌ Invalid date format. Use MM-DD format (e.g., 07-10)")
            sys.exit(1)
        
        delete_event_by_date(args.date, force=args.force)
    elif args.all:
        delete_all_events(force=args.force)

if __name__ == '__main__':
    main()