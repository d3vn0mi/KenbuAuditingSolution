from datetime import datetime, timezone
from ..extensions import db


class AuditSession(db.Model):
    __tablename__ = 'audit_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    standard_id = db.Column(db.Integer, db.ForeignKey('standards.id'), nullable=True)
    status = db.Column(db.String(20), default='draft')  # draft, in_progress, completed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text)

    # Relationships
    user = db.relationship('User', lazy='joined')
    standard = db.relationship('Standard', lazy='joined')
    assets = db.relationship('AuditAsset', backref='session', lazy='dynamic',
                             cascade='all, delete-orphan')

    @property
    def total_checks(self):
        return AuditResult.query.join(AuditAsset).filter(
            AuditAsset.session_id == self.id
        ).count()

    @property
    def checked_count(self):
        return AuditResult.query.join(AuditAsset).filter(
            AuditAsset.session_id == self.id,
            AuditResult.status != 'not_checked'
        ).count()

    @property
    def progress(self):
        total = self.total_checks
        if total == 0:
            return 0
        return int((self.checked_count / total) * 100)

    @property
    def pass_count(self):
        return AuditResult.query.join(AuditAsset).filter(
            AuditAsset.session_id == self.id,
            AuditResult.status == 'pass'
        ).count()

    @property
    def fail_count(self):
        return AuditResult.query.join(AuditAsset).filter(
            AuditAsset.session_id == self.id,
            AuditResult.status == 'fail'
        ).count()

    @property
    def na_count(self):
        return AuditResult.query.join(AuditAsset).filter(
            AuditAsset.session_id == self.id,
            AuditResult.status == 'not_applicable'
        ).count()

    def __repr__(self):
        return f'<AuditSession {self.id} {self.title}>'


class AuditAsset(db.Model):
    __tablename__ = 'audit_assets'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('audit_sessions.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    benchmarks = db.relationship('AuditAssetBenchmark', backref='asset',
                                 lazy='joined', cascade='all, delete-orphan')
    results = db.relationship('AuditResult', backref='asset',
                              lazy='dynamic', cascade='all, delete-orphan')

    @property
    def total_checks(self):
        return self.results.count()

    @property
    def checked_count(self):
        return self.results.filter(AuditResult.status != 'not_checked').count()

    @property
    def progress(self):
        total = self.total_checks
        if total == 0:
            return 0
        return int((self.checked_count / total) * 100)

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
        return f'<AuditAsset {self.name}>'


class AuditAssetBenchmark(db.Model):
    __tablename__ = 'audit_asset_benchmarks'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('audit_assets.id'), nullable=False)
    benchmark_id = db.Column(db.Integer, db.ForeignKey('benchmarks.id'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('asset_id', 'benchmark_id', name='uq_audit_asset_benchmark'),
    )

    benchmark = db.relationship('Benchmark', lazy='joined')

    def __repr__(self):
        return f'<AuditAssetBenchmark asset={self.asset_id} benchmark={self.benchmark_id}>'


class AuditResult(db.Model):
    __tablename__ = 'audit_results'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('audit_assets.id'), nullable=False)
    check_id = db.Column(db.Integer, db.ForeignKey('checks.id'), nullable=False)
    status = db.Column(db.String(20), default='not_checked')  # pass, fail, not_applicable, not_checked
    finding = db.Column(db.Text)
    checked_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('asset_id', 'check_id', name='uq_audit_asset_check'),
    )

    check = db.relationship('Check', lazy='joined')

    def __repr__(self):
        return f'<AuditResult asset={self.asset_id} check={self.check_id} {self.status}>'
