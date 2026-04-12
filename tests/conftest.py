import pytest
from app import create_app
from app.extensions import db as _db
from app.models import (
    User, Platform, Benchmark, BenchmarkSection, Check,
)


@pytest.fixture(scope='session')
def app():
    """Create the Flask application with testing config."""
    app = create_app('testing')
    yield app


@pytest.fixture(scope='session')
def _database(app):
    """Create all tables once per test session."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture(autouse=True)
def db_session(app, _database):
    """Provide a clean database for each test."""
    with app.app_context():
        yield _database
        _database.session.remove()
        for table in reversed(_database.metadata.sorted_tables):
            _database.session.execute(table.delete())
        _database.session.commit()


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


def _create_user(db, username, password, role='auditor', is_approved=True):
    """Helper to create a user and return them."""
    user = User(
        username=username,
        display_name=username,
        role=role,
        is_approved=is_approved,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username, password):
    """Helper to log in a user via the test client."""
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


@pytest.fixture()
def auditor_user(db_session):
    """Create an approved auditor user."""
    return _create_user(db_session, 'testauditor', 'password123', role='auditor')


@pytest.fixture()
def auth_client(app, client, auditor_user):
    """Test client logged in as an approved auditor."""
    _login(client, 'testauditor', 'password123')
    return client


@pytest.fixture()
def admin_user(db_session):
    """Create an approved admin user."""
    return _create_user(db_session, 'testadmin', 'password123', role='admin')


@pytest.fixture()
def admin_client(app, client, admin_user):
    """Test client logged in as an approved admin."""
    _login(client, 'testadmin', 'password123')
    return client


@pytest.fixture()
def seed_data(db_session):
    """Seed minimal benchmark data for tests."""
    platform = Platform(
        name='Test Linux',
        slug='test-linux',
        os_family='Linux',
        icon='linux',
        description='Test platform',
    )
    db_session.session.add(platform)
    db_session.session.flush()

    benchmark = Benchmark(
        name='Test CIS Benchmark',
        version='1.0',
        platform_id=platform.id,
        description='Test benchmark for tests',
    )
    db_session.session.add(benchmark)
    db_session.session.flush()

    section = BenchmarkSection(
        benchmark_id=benchmark.id,
        parent_id=None,
        number='1',
        title='Test Section',
        description='Test section description',
        sort_order=0,
    )
    db_session.session.add(section)
    db_session.session.flush()

    checks = []
    for i, (num, level) in enumerate([('1.1', 1), ('1.2', 2), ('1.3', 1)]):
        check = Check(
            section_id=section.id,
            check_number=num,
            title=f'Test Check {num}',
            description=f'Description for check {num}',
            rationale=f'Rationale for check {num}',
            level=level,
            scored=True,
            audit_command=f'echo "audit {num}"',
            expected_output=f'Expected output for {num}',
            remediation=f'Remediation for {num}',
            sort_order=i,
        )
        db_session.session.add(check)
        checks.append(check)

    db_session.session.flush()

    return {
        'platform': platform,
        'benchmark': benchmark,
        'section': section,
        'checks': checks,
    }
