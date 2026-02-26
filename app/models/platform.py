from ..extensions import db


class Platform(db.Model):
    __tablename__ = 'platforms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    os_family = db.Column(db.String(30), nullable=False)  # Linux, Windows, macOS, Network
    icon = db.Column(db.String(50))
    description = db.Column(db.Text)

    # Relationships
    benchmarks = db.relationship('Benchmark', backref='platform', lazy='dynamic')

    def __repr__(self):
        return f'<Platform {self.name}>'
