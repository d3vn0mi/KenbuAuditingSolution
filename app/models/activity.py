from datetime import datetime, timezone
from ..extensions import db


class ActivityLog(db.Model):
    """Who-changed-what trail. One row per successful state-changing request."""
    __tablename__ = 'activity_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(80))  # snapshot (survives user deletion)
    method = db.Column(db.String(10))
    endpoint = db.Column(db.String(120))
    path = db.Column(db.String(300))
    status_code = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return f'<ActivityLog {self.username} {self.method} {self.endpoint}>'
