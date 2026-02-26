from ..extensions import db


class Benchmark(db.Model):
    __tablename__ = 'benchmarks'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    version = db.Column(db.String(20), nullable=False)
    platform_id = db.Column(db.Integer, db.ForeignKey('platforms.id'), nullable=False)
    release_date = db.Column(db.Date)
    description = db.Column(db.Text)
    url = db.Column(db.String(500))

    # Relationships
    sections = db.relationship('BenchmarkSection', backref='benchmark', lazy='dynamic')
    audit_sessions = db.relationship('AuditSession', backref='benchmark', lazy='dynamic')

    @property
    def total_checks(self):
        from .check import Check
        return Check.query.join(BenchmarkSection).filter(
            BenchmarkSection.benchmark_id == self.id
        ).count()

    def __repr__(self):
        return f'<Benchmark {self.name} v{self.version}>'


class BenchmarkSection(db.Model):
    __tablename__ = 'benchmark_sections'

    id = db.Column(db.Integer, primary_key=True)
    benchmark_id = db.Column(db.Integer, db.ForeignKey('benchmarks.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('benchmark_sections.id'), nullable=True)
    number = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)

    # Self-referential relationship
    children = db.relationship(
        'BenchmarkSection',
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic',
        order_by='BenchmarkSection.sort_order'
    )
    checks = db.relationship('Check', backref='section', lazy='dynamic',
                             order_by='Check.sort_order')

    @property
    def total_checks(self):
        """Count checks in this section and all subsections recursively."""
        count = self.checks.count()
        for child in self.children:
            count += child.total_checks
        return count

    def __repr__(self):
        return f'<Section {self.number} {self.title}>'
