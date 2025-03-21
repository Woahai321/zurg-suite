from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class TaskSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cron = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_run = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        # Extract action name without the '_schedule' suffix if present
        display_name = self.name
        if display_name.endswith(' Schedule'):
            display_name = display_name[:-9]
            
        # The frontend expects different field names than our database schema
        return {
            'id': self.id,
            'name': display_name,
            'task_name': self.action,
            'cron_expression': self.cron,
            'enabled': self.enabled,
            'schedule_type': 'cron',  # Default to cron type for imported schedules
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_run': self.last_run.isoformat() if self.last_run else None
        }

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50), default='info')  # info, success, error, warning
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'type': self.type,
            'timestamp': self.timestamp.isoformat()
        } 