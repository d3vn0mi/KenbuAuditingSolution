from ..extensions import db


class Check(db.Model):
    __tablename__ = 'checks'

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('benchmark_sections.id'), nullable=False)
    check_number = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    rationale = db.Column(db.Text)
    level = db.Column(db.Integer, nullable=False, default=1)  # CIS Level 1 or 2
    scored = db.Column(db.Boolean, nullable=False, default=True)
    audit_command = db.Column(db.Text)  # CLI command for verification
    audit_steps = db.Column(db.Text)    # GUI steps (Windows/macOS)
    expected_output = db.Column(db.Text, nullable=False)
    remediation = db.Column(db.Text)
    references = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)

    # Relationships
    audit_results = db.relationship('AuditResult', backref='check', lazy='dynamic')

    @property
    def level_display(self):
        return f'L{self.level}'

    @property
    def scored_display(self):
        return 'Scored' if self.scored else 'Not Scored'

    @property
    def benchmark(self):
        return self.section.benchmark

    def __repr__(self):
        return f'<Check {self.check_number} {self.title}>'
