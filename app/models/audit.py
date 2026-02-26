from datetime import datetime, timezone
from ..extensions import db


class AuditSession(db.Model):
    __tablename__ = 'audit_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    benchmark_id = db.Column(db.Integer, db.ForeignKey('benchmarks.id'), nullable=False)
    target_name = db.Column(db.String(200))
    target_ip = db.Column(db.String(45))
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed
    notes = db.Column(db.Text)

    # Relationships
    results = db.relationship('AuditResult', backref='session', lazy='dynamic',
                              cascade='all, delete-orphan')

    @property
    def progress(self):
        total = self.results.count()
        if total == 0:
            return 0
        checked = self.results.filter(AuditResult.status != 'not_checked').count()
        return int((checked / total) * 100)

    @property
    def pass_count(self):
        return self.results.filter_by(status='pass').count()

    @property
    def fail_count(self):
        return self.results.filter_by(status='fail').count()

    @property
    def na_count(self):
        return self.results.filter_by(status='not_applicable').count()

    def __repr__(self):
        return f'<AuditSession {self.id} {self.target_name}>'


class AuditResult(db.Model):
    __tablename__ = 'audit_results'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('audit_sessions.id'), nullable=False)
    check_id = db.Column(db.Integer, db.ForeignKey('checks.id'), nullable=False)
    status = db.Column(db.String(20), default='not_checked')  # pass, fail, not_applicable, not_checked
    finding = db.Column(db.Text)
    checked_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('session_id', 'check_id', name='uq_session_check'),
    )

    def __repr__(self):
        return f'<AuditResult {self.session_id}:{self.check_id} {self.status}>'
