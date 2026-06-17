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


# Domains used to group controls in the register / dashboard heatmap.
CONTROL_DOMAINS = [
    'ISMS', 'IAM', 'Crypto', 'SupplyChain', 'TLPT', 'IncidentMgmt',
    'BCDR', 'RiskManagement', 'PhysicalResilience', 'AssetManagement',
]

# Cross-framework reference catalogues a control can be mapped to.
REFERENCE_FRAMEWORKS = [
    'ISO27001', 'NIST_IR_8270', 'NIST_IR_8401', 'ECSS', 'CCSDS', 'ENISA_SPACE',
]


# A control can satisfy many obligations (across regulations); an obligation can
# be satisfied by many controls. This M:N join is the cross-framework synthesis.
control_obligations = db.Table(
    'control_obligations',
    db.Column('control_id', db.Integer, db.ForeignKey('controls.id'), primary_key=True),
    db.Column('obligation_id', db.Integer, db.ForeignKey('obligations.id'), primary_key=True),
)

# A control is evidenced by existing technical checks (CIS, etc.). This is the
# link that lets a passing check serve as evidence for a regulatory control.
control_checks = db.Table(
    'control_checks',
    db.Column('control_id', db.Integer, db.ForeignKey('controls.id'), primary_key=True),
    db.Column('check_id', db.Integer, db.ForeignKey('checks.id'), primary_key=True),
)


class Obligation(db.Model):
    """A regulatory obligation (article / sub-article), hierarchical per regulation."""
    __tablename__ = 'obligations'

    id = db.Column(db.Integer, primary_key=True)
    regulation_id = db.Column(db.Integer, db.ForeignKey('regulations.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('obligations.id'), nullable=True)
    ref = db.Column(db.String(50), nullable=False)  # "Art.21(2)(d)"
    title = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    content_hash = db.Column(db.String(64))  # sha256 for delta detection (see DESIGN §6)

    __table_args__ = (
        db.UniqueConstraint('regulation_id', 'ref', name='uq_obligation_regulation_ref'),
    )

    regulation = db.relationship('Regulation', backref=db.backref('obligations', lazy='dynamic'))
    children = db.relationship(
        'Obligation',
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic',
        order_by='Obligation.sort_order',
    )

    def __repr__(self):
        return f'<Obligation {self.ref}>'


class Control(db.Model):
    """An implementable control — the cross-framework hub.

    Links to obligations (many regulations) and to existing technical checks, so a
    passing check evidences a regulatory control across frameworks.
    """
    __tablename__ = 'controls'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True, index=True)  # "SC-01"
    title = db.Column(db.String(300), nullable=False)
    domain = db.Column(db.String(50))  # see CONTROL_DOMAINS
    description = db.Column(db.Text)
    guidance = db.Column(db.Text)

    obligations = db.relationship('Obligation', secondary=control_obligations,
                                  backref='controls')
    checks = db.relationship('Check', secondary=control_checks, backref='controls')
    evidence_requirements = db.relationship('EvidenceRequirement', backref='control',
                                            cascade='all, delete-orphan')
    references = db.relationship('ControlReference', backref='control',
                                cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Control {self.code}>'


class EvidenceRequirement(db.Model):
    """What proves a control is implemented (a document, config, test result...)."""
    __tablename__ = 'evidence_requirements'

    id = db.Column(db.Integer, primary_key=True)
    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(30))  # document | config | test_result | attestation
    cadence_days = db.Column(db.Integer, nullable=True)  # review/refresh cadence

    def __repr__(self):
        return f'<EvidenceRequirement {self.title}>'


class ControlReference(db.Model):
    """Cross-map to an external standard (ISO 27001, NIST IR, ECSS, CCSDS, ENISA)."""
    __tablename__ = 'control_references'

    id = db.Column(db.Integer, primary_key=True)
    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=False)
    framework = db.Column(db.String(40), nullable=False)  # see REFERENCE_FRAMEWORKS
    ref_code = db.Column(db.String(50))  # "A.5.19"
    title = db.Column(db.String(300))

    def __repr__(self):
        return f'<ControlReference {self.framework} {self.ref_code}>'
