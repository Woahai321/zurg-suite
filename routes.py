from flask import Blueprint, jsonify, render_template, request
from models import db, ActivityLog
from datetime import datetime, timedelta

bp = Blueprint('routes', __name__)

@bp.route('/')
def index():
    return render_template('dashboard.html')

@bp.route('/recent_logs')
def recent_logs():
    # Get logs from the last 24 hours
    since = datetime.utcnow() - timedelta(hours=24)
    logs = ActivityLog.query.filter(ActivityLog.timestamp >= since).order_by(ActivityLog.timestamp.desc()).limit(50).all()
    
    return jsonify({
        'logs': [log.to_dict() for log in logs]
    })

@bp.route('/trigger/<action>', methods=['POST'])
def trigger_action(action):
    try:
        # Your existing action handling code here
        
        # Log the action
        log = ActivityLog(
            message=f"{action.replace('_', ' ').title()} action triggered",
            type='info'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        # Log the error
        log = ActivityLog(
            message=f"Error triggering {action}: {str(e)}",
            type='error'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/status')
def get_status():
    # Your existing status code here
    return jsonify({
        'workers': {
            'total': 10,
            'running': 5,
            'free': 5
        },
        'system': {
            'memory_usage': 45,
            'memory_allocation': 1024,
            'system_memory': 8192
        }
    })

@bp.route('/clear_notifications', methods=['POST'])
def clear_notifications():
    try:
        # Delete all activity logs
        ActivityLog.query.delete()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}) 