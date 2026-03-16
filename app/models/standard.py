from ..extensions import db


class Standard(db.Model):
    __tablename__ = 'standards'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(50), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    version = db.Column(db.String(20))

    checks = db.relationship('StandardCheck', backref='standard', lazy='dynamic',
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Standard {self.name}>'


class StandardCheck(db.Model):
    __tablename__ = 'standard_checks'

    id = db.Column(db.Integer, primary_key=True)
    standard_id = db.Column(db.Integer, db.ForeignKey('standards.id'), nullable=False)
    check_id = db.Column(db.Integer, db.ForeignKey('checks.id'), nullable=False)
    article = db.Column(db.String(50))
    requirement = db.Column(db.String(300))

    __table_args__ = (
        db.UniqueConstraint('standard_id', 'check_id', name='uq_standard_check'),
    )

    check = db.relationship('Check', lazy='joined')

    def __repr__(self):
        return f'<StandardCheck standard={self.standard_id} check={self.check_id}>'
