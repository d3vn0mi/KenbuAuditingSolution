from ..extensions import db


# Legislative maturity of a regulation. The EU Space Act is still a proposal in
# trilogue, so status is first-class and versioned (see DESIGN_compliance §6).
REGULATION_STATUSES = ['proposal', 'in_trilogue', 'adopted', 'in_force']


class Regulation(db.Model):
    """A regulatory instrument (EU Space Act, NIS2, CER, CSA2, GDPR, ...).

    Evolution of the former ``Standard`` model: adds short_code, legislative
    status, effective date and source URL so the regulatory layer can track
    in-flux instruments and stamp evidence/readiness packs with a version.
    """
    __tablename__ = 'regulations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    short_code = db.Column(db.String(20))  # "EUSA", "NIS2", "CER", "CSA2"
    slug = db.Column(db.String(50), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    version = db.Column(db.String(20))
    status = db.Column(db.String(20), default='in_force')  # see REGULATION_STATUSES
    effective_date = db.Column(db.Date, nullable=True)
    source_url = db.Column(db.String(500), nullable=True)

    checks = db.relationship('RegulationCheck', backref='regulation', lazy='dynamic',
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Regulation {self.short_code or self.name}>'


class RegulationCheck(db.Model):
    """Direct regulation->check mapping (legacy convenience).

    Superseded for new content by the Control hub (Control<->Check), but retained
    so existing audit-session filtering and the curated NIS2->CIS mappings keep
    working until controls are seeded. See ADR 0001.
    """
    __tablename__ = 'regulation_checks'

    id = db.Column(db.Integer, primary_key=True)
    regulation_id = db.Column(db.Integer, db.ForeignKey('regulations.id'), nullable=False)
    check_id = db.Column(db.Integer, db.ForeignKey('checks.id'), nullable=False)
    article = db.Column(db.String(50))
    requirement = db.Column(db.String(300))

    __table_args__ = (
        db.UniqueConstraint('regulation_id', 'check_id', name='uq_regulation_check'),
    )

    check = db.relationship('Check', lazy='joined')

    def __repr__(self):
        return f'<RegulationCheck regulation={self.regulation_id} check={self.check_id}>'
