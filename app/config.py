import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'kenbu-dev-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = False

    # GitHub OAuth SSO
    GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

    # Evidence encryption at rest (Fernet). Primary key + optional older keys
    # (comma-separated) so key rotation is not a data migration.
    EVIDENCE_ENCRYPTION_KEY = os.environ.get('EVIDENCE_ENCRYPTION_KEY')
    EVIDENCE_ENCRYPTION_KEYS_OLD = os.environ.get('EVIDENCE_ENCRYPTION_KEYS_OLD', '')


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://kenbu:kenbu@db:5432/kenbu'
    )
    # Fixed dev fallback so local uploads work; NEVER use in production.
    EVIDENCE_ENCRYPTION_KEY = os.environ.get(
        'EVIDENCE_ENCRYPTION_KEY',
        'SX1boVzg4TALo_wZRFMEip21ML3GS5wqSSKY4aZBOZs=')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    # Fixed, valid Fernet key for deterministic tests.
    EVIDENCE_ENCRYPTION_KEY = '1ZwnBzqhLr7LHAe9zxzD4nhg0EX8U1xXwAEpMrokQFE='


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY', '')

    def __init__(self):
        super().__init__()
        if not self.SECRET_KEY:
            raise RuntimeError('SECRET_KEY environment variable must be set in production')
        # Fail closed: never silently store evidence unencrypted in production.
        if not self.EVIDENCE_ENCRYPTION_KEY:
            raise RuntimeError('EVIDENCE_ENCRYPTION_KEY environment variable must be set in production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://kenbu:kenbu@db:5432/kenbu'
    )


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}
