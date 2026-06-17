from datetime import datetime, timezone, timedelta
from ..extensions import db


INCIDENT_STATUSES = ['open', 'contained', 'closed']
INCIDENT_SEVERITIES = ['critical', 'high', 'medium', 'low']

# NIS2 Article 23 statutory reporting deadlines, measured from detection.
EARLY_WARNING_HOURS = 24
NOTIFICATION_HOURS = 72
FINAL_REPORT_DAYS = 30  # NIS2 "one month" (approximated as 30 days)


class Incident(db.Model):
    """A reportable incident with the NIS2 Article 23 statutory clock."""
    __tablename__ = 'incidents'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    regulation_id = db.Column(db.Integer, db.ForeignKey('regulations.id'), nullable=True)
    reference = db.Column(db.String(40), nullable=True)
    title = db.Column(db.String(300), nullable=False)
    severity = db.Column(db.String(20), default='high')
    status = db.Column(db.String(20), default='open')
    description = db.Column(db.Text, nullable=True)
    affected_systems = db.Column(db.Text, nullable=True)

    detected_at = db.Column(db.DateTime, nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    early_warning_sent_at = db.Column(db.DateTime, nullable=True)
    notification_sent_at = db.Column(db.DateTime, nullable=True)
    final_report_sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    regulation = db.relationship('Regulation', lazy='joined')

    @property
    def early_warning_due(self):
        return self.detected_at + timedelta(hours=EARLY_WARNING_HOURS)

    @property
    def notification_due(self):
        return self.detected_at + timedelta(hours=NOTIFICATION_HOURS)

    @property
    def final_report_due(self):
        return self.detected_at + timedelta(days=FINAL_REPORT_DAYS)

    def __repr__(self):
        return f'<Incident {self.id} {self.title}>'
