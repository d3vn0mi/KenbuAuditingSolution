from datetime import datetime, timezone
from ..extensions import db
from .pentest import SEVERITY_LEVELS  # critical/high/medium/low/informational


FINDING_SOURCES = ['tlpt', 'pentest', 'internal', 'scan', 'other']
FINDING_STATUSES = ['open', 'remediated', 'accepted', 'false_positive']


# A finding (from RAVEN TLPT, pentest, internal review, or a scan) attaches to
# controls. Open high/critical findings cap a control's effective readiness — the
# offensive-led differentiator pure-GRC tools cannot offer (see DESIGN §7).
finding_controls = db.Table(
    'finding_controls',
    db.Column('finding_id', db.Integer, db.ForeignKey('findings.id'), primary_key=True),
    db.Column('control_id', db.Integer, db.ForeignKey('controls.id'), primary_key=True),
)


class Finding(db.Model):
    __tablename__ = 'findings'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    title = db.Column(db.String(300), nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # see SEVERITY_LEVELS
    source = db.Column(db.String(20), default='internal')  # see FINDING_SOURCES
    description = db.Column(db.Text, nullable=True)
    remediation = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='open')  # see FINDING_STATUSES
    discovered_at = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    promoted_from_pentest_finding_id = db.Column(
        db.Integer, db.ForeignKey('pentest_findings.id'), nullable=True)

    controls = db.relationship('Control', secondary=finding_controls, backref='findings')

    @property
    def is_open(self):
        return self.status == 'open'

    def __repr__(self):
        return f'<Finding {self.id} {self.title} ({self.severity})>'
