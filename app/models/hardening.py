from datetime import datetime, timezone
from ..extensions import db


class HardeningTask(db.Model):
    __tablename__ = 'hardening_tasks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='draft')  # draft, in_progress, completed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    assets = db.relationship('HardeningAsset', backref='task', lazy='dynamic',
                             cascade='all, delete-orphan')

    @property
    def total_items(self):
        return HardeningCheckResult.query.join(HardeningAsset).filter(
            HardeningAsset.task_id == self.id
        ).count()

    @property
    def completed_items(self):
        return HardeningCheckResult.query.join(HardeningAsset).filter(
            HardeningAsset.task_id == self.id,
            HardeningCheckResult.status.in_(['done', 'skipped'])
        ).count()

    @property
    def progress(self):
        total = self.total_items
        if total == 0:
            return 0
        return int((self.completed_items / total) * 100)

    def __repr__(self):
        return f'<HardeningTask {self.title}>'


class HardeningAsset(db.Model):
    __tablename__ = 'hardening_assets'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('hardening_tasks.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    benchmarks = db.relationship('HardeningAssetBenchmark', backref='asset',
                                 lazy='joined', cascade='all, delete-orphan')
    check_results = db.relationship('HardeningCheckResult', backref='asset',
                                    lazy='dynamic', cascade='all, delete-orphan')

    @property
    def total_checks(self):
        return self.check_results.count()

    @property
    def completed_checks(self):
        return self.check_results.filter(
            HardeningCheckResult.status.in_(['done', 'skipped'])
        ).count()

    @property
    def progress(self):
        total = self.total_checks
        if total == 0:
            return 0
        return int((self.completed_checks / total) * 100)

    def __repr__(self):
        return f'<HardeningAsset {self.name}>'


class HardeningAssetBenchmark(db.Model):
    __tablename__ = 'hardening_asset_benchmarks'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('hardening_assets.id'), nullable=False)
    benchmark_id = db.Column(db.Integer, db.ForeignKey('benchmarks.id'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('asset_id', 'benchmark_id', name='uq_asset_benchmark'),
    )

    benchmark = db.relationship('Benchmark', lazy='joined')

    def __repr__(self):
        return f'<HardeningAssetBenchmark asset={self.asset_id} benchmark={self.benchmark_id}>'


class HardeningCheckResult(db.Model):
    __tablename__ = 'hardening_check_results'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('hardening_assets.id'), nullable=False)
    check_id = db.Column(db.Integer, db.ForeignKey('checks.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, done, skipped
    notes = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('asset_id', 'check_id', name='uq_asset_check'),
    )

    check = db.relationship('Check', lazy='joined')

    def __repr__(self):
        return f'<HardeningCheckResult asset={self.asset_id} check={self.check_id} status={self.status}>'
