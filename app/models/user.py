from datetime import datetime, timezone
import pyotp
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db, login_manager


VALID_ROLES = ['admin', 'auditor', 'security_engineer', 'user']

ROLE_PERMISSIONS = {
    'admin': {'audits', 'hardening', 'pentests', 'admin'},
    'auditor': {'audits', 'hardening', 'pentests'},
    'security_engineer': {'hardening'},
    'user': set(),
}


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    display_name = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Role and approval
    role = db.Column(db.String(20), default='user')
    is_approved = db.Column(db.Boolean, default=False)

    # OAuth fields
    auth_provider = db.Column(db.String(20), default='local')  # 'local' or 'github'
    github_id = db.Column(db.Integer, unique=True, nullable=True, index=True)
    avatar_url = db.Column(db.String(500), nullable=True)

    # MFA fields
    mfa_secret = db.Column(db.String(32), nullable=True)
    mfa_enabled = db.Column(db.Boolean, default=False)

    # Relationships
    audit_sessions = db.relationship('AuditSession', backref='auditor', lazy='dynamic')

    @property
    def is_admin(self):
        return self.role == 'admin'

    def can_access(self, feature):
        return feature in ROLE_PERMISSIONS.get(self.role, set())

    @property
    def can_audit(self):
        return self.can_access('audits')

    @property
    def can_harden(self):
        return self.can_access('hardening')

    @property
    def can_pentest(self):
        return self.can_access('pentests')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def generate_mfa_secret(self):
        self.mfa_secret = pyotp.random_base32()
        return self.mfa_secret

    def get_mfa_uri(self):
        if not self.mfa_secret:
            return None
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.provisioning_uri(name=self.username, issuer_name='Kenbu')

    def verify_mfa_token(self, token):
        if not self.mfa_secret:
            return False
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token, valid_window=1)

    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
