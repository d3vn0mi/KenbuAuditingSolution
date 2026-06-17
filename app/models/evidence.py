from datetime import datetime, timezone, date
from ..extensions import db


EVIDENCE_TYPES = ['document', 'config', 'test_result', 'attestation', 'other']


# Evidence links to regulatory controls and/or directly to technical checks
# (so an audit result can double as control evidence).
evidence_controls = db.Table(
    'evidence_controls',
    db.Column('evidence_id', db.Integer, db.ForeignKey('evidence.id'), primary_key=True),
    db.Column('control_id', db.Integer, db.ForeignKey('controls.id'), primary_key=True),
)

evidence_checks = db.Table(
    'evidence_checks',
    db.Column('evidence_id', db.Integer, db.ForeignKey('evidence.id'), primary_key=True),
    db.Column('check_id', db.Integer, db.ForeignKey('checks.id'), primary_key=True),
)


class Evidence(db.Model):
    """A logical evidence artifact (with version history) proving one or more
    controls/checks. Files are stored encrypted at rest (see utils/evidence_store)."""
    __tablename__ = 'evidence'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    evidence_type = db.Column(db.String(30), default='document')
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    valid_until = db.Column(db.Date, nullable=True)
    review_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    owner = db.relationship('User', lazy='joined')
    versions = db.relationship('EvidenceVersion', backref='evidence',
                               lazy='dynamic', cascade='all, delete-orphan',
                               order_by='EvidenceVersion.version.desc()')
    controls = db.relationship('Control', secondary=evidence_controls, backref='evidence')
    checks = db.relationship('Check', secondary=evidence_checks, backref='evidence')

    @property
    def current_version(self):
        return self.versions.first()

    @property
    def is_expired(self):
        return self.valid_until is not None and self.valid_until < date.today()

    @property
    def expiring_soon(self):
        if self.valid_until is None:
            return False
        delta = (self.valid_until - date.today()).days
        return 0 <= delta <= 30

    def __repr__(self):
        return f'<Evidence {self.id} {self.title}>'


class EvidenceVersion(db.Model):
    """One uploaded version of an evidence artifact, with its integrity hash."""
    __tablename__ = 'evidence_versions'

    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)   # sha256 of plaintext
    storage_name = db.Column(db.String(64), nullable=False)   # uuid hex on disk
    original_filename = db.Column(db.String(300))
    mime = db.Column(db.String(100))
    size = db.Column(db.Integer)
    collected_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    note = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('evidence_id', 'version', name='uq_evidence_version'),
    )

    def __repr__(self):
        return f'<EvidenceVersion evidence={self.evidence_id} v{self.version}>'
