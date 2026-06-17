from datetime import datetime, timezone
from ..extensions import db


# Implementation status of a control within an assessment.
CONTROL_STATUSES = ['not_started', 'planned', 'partial', 'implemented', 'not_applicable']

# Score contribution per status; not_applicable is excluded from the denominator.
STATUS_SCORE = {
    'not_started': 0.0,
    'planned': 0.25,
    'partial': 0.5,
    'implemented': 1.0,
}

ASSESSMENT_STATUSES = ['draft', 'active', 'archived']


class Organization(db.Model):
    """Tenant anchor. MVP runs a single default organization per deployment;
    nullable organization_id columns on top-level entities allow enabling full
    multi-tenancy later without a destructive migration (ADR 0003)."""
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(50), nullable=False, unique=True, index=True)

    def __repr__(self):
        return f'<Organization {self.slug}>'


class ReadinessAssessment(db.Model):
    """A per-organization compliance assessment against a regulation (or, when
    regulation_id is NULL, cross-regulation)."""
    __tablename__ = 'readiness_assessments'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    regulation_id = db.Column(db.Integer, db.ForeignKey('regulations.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='draft')  # see ASSESSMENT_STATUSES
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    regulation = db.relationship('Regulation', lazy='joined')
    owner = db.relationship('User', lazy='joined')
    control_statuses = db.relationship('ControlStatus', backref='assessment',
                                       lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ReadinessAssessment {self.id} {self.title}>'


class ControlStatus(db.Model):
    """Implementation status of one control within a readiness assessment."""
    __tablename__ = 'control_statuses'

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('readiness_assessments.id'), nullable=False)
    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=False)
    status = db.Column(db.String(20), default='not_started')  # see CONTROL_STATUSES
    maturity = db.Column(db.Integer, nullable=True)  # 0-5
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    target_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('assessment_id', 'control_id', name='uq_control_status'),
    )

    control = db.relationship('Control', lazy='joined')
    owner = db.relationship('User', lazy='joined')

    def __repr__(self):
        return f'<ControlStatus assessment={self.assessment_id} control={self.control_id} {self.status}>'
