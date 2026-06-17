from datetime import datetime, timezone
from ..extensions import db


SUPPLIER_CRITICALITY = ['high', 'medium', 'low']
SUPPLIER_STATUSES = ['under_review', 'approved', 'rejected', 'active']


# Suppliers map to supply-chain controls (CSA2 / Space Act supply-chain RM).
supplier_controls = db.Table(
    'supplier_controls',
    db.Column('supplier_id', db.Integer, db.ForeignKey('suppliers.id'), primary_key=True),
    db.Column('control_id', db.Integer, db.ForeignKey('controls.id'), primary_key=True),
)


class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(200), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    criticality = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='under_review')
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    controls = db.relationship('Control', secondary=supplier_controls, backref='suppliers')
    sboms = db.relationship('SBOM', backref='supplier', lazy='dynamic',
                            cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Supplier {self.name}>'


class SBOM(db.Model):
    __tablename__ = 'sboms'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    name = db.Column(db.String(200), nullable=True)
    format = db.Column(db.String(20))  # cyclonedx | spdx | unknown
    original_filename = db.Column(db.String(300))
    component_count = db.Column(db.Integer, default=0)
    raw_size = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    components = db.relationship('SBOMComponent', backref='sbom', lazy='dynamic',
                                cascade='all, delete-orphan')

    def __repr__(self):
        return f'<SBOM {self.id} {self.format} ({self.component_count})>'


class SBOMComponent(db.Model):
    __tablename__ = 'sbom_components'

    id = db.Column(db.Integer, primary_key=True)
    sbom_id = db.Column(db.Integer, db.ForeignKey('sboms.id'), nullable=False)
    name = db.Column(db.String(300), nullable=False)
    version = db.Column(db.String(100))
    purl = db.Column(db.String(500))
    license = db.Column(db.String(200))

    def __repr__(self):
        return f'<SBOMComponent {self.name}@{self.version}>'
