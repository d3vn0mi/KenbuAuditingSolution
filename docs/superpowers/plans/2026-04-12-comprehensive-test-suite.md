# Comprehensive Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pytest-based test suite covering all critical paths (auth, benchmarks, audits, hardening, pentests, export, seeding) to provide pre-release confidence and ongoing regression protection.

**Architecture:** Flask test client with SQLite in-memory database via the existing `TestingConfig`. Session-scoped app and tables, function-scoped transaction rollback for test isolation. Minimal fixture data for fast tests.

**Tech Stack:** pytest, pytest-cov, Flask test client, SQLite in-memory, pyotp (for MFA tests)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `requirements.txt` | Add pytest, pytest-cov dependencies |
| `tests/conftest.py` | App factory, DB setup, auth fixtures, seed data fixtures |
| `tests/test_auth.py` | Registration, login, logout, MFA, protected route access |
| `tests/test_benchmarks.py` | Benchmark listing, detail, section, check detail, search |
| `tests/test_audits.py` | Audit session CRUD, asset management, result tracking, lifecycle |
| `tests/test_hardening.py` | Hardening task CRUD, asset management, check tracking, lifecycle |
| `tests/test_pentests.py` | Assessment CRUD, phases, checklist items, findings, team management |
| `tests/test_export.py` | Excel export for benchmarks, audits, hardening |
| `tests/test_seed.py` | Platform seeding, benchmark YAML loading, full seed_all |

---

### Task 1: Add test dependencies and create conftest.py

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Add pytest and pytest-cov to requirements.txt**

Add these two lines at the end of `requirements.txt`:

```
pytest
pytest-cov
```

- [ ] **Step 2: Create empty tests/__init__.py**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 3: Create tests/conftest.py with all shared fixtures**

```python
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
    """Wrap each test in a transaction that rolls back after the test."""
    with app.app_context():
        connection = _database.engine.connect()
        transaction = connection.begin()
        options = dict(bind=connection, binds={})
        session = _database.create_scoped_session(options=options)
        old_session = _database.session
        _database.session = session

        yield _database

        transaction.rollback()
        connection.close()
        session.remove()
        _database.session = old_session


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
```

- [ ] **Step 4: Install dependencies and verify fixtures load**

Run: `cd /home/d3vn0mi/Desktop/opt/Kenbu-auditing-tool && pip install pytest pytest-cov`
Expected: successful install

Run: `cd /home/d3vn0mi/Desktop/opt/Kenbu-auditing-tool && python -m pytest tests/ -v --collect-only`
Expected: "no tests ran" but no import errors

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/__init__.py tests/conftest.py
git commit -m "Add pytest infrastructure and shared test fixtures"
```

---

### Task 2: Write auth tests

**Files:**
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write tests/test_auth.py**

```python
import pyotp
import pytest
from app.models import User


class TestRegister:
    def test_register_valid_user(self, client, db_session):
        resp = client.post('/auth/register', data={
            'username': 'newuser',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
            'display_name': 'New User',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Account created' in resp.data
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.is_approved is False

    def test_register_mismatched_passwords(self, client, db_session):
        resp = client.post('/auth/register', data={
            'username': 'newuser',
            'password': 'securepass123',
            'confirm_password': 'differentpass',
            'display_name': 'New User',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Passwords do not match' in resp.data

    def test_register_short_password(self, client, db_session):
        resp = client.post('/auth/register', data={
            'username': 'newuser',
            'password': 'short',
            'confirm_password': 'short',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'at least 8 characters' in resp.data

    def test_register_duplicate_username(self, client, db_session, auditor_user):
        resp = client.post('/auth/register', data={
            'username': 'testauditor',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'already exists' in resp.data


class TestLogin:
    def test_login_approved_user(self, client, auditor_user):
        resp = client.post('/auth/login', data={
            'username': 'testauditor',
            'password': 'password123',
        }, follow_redirects=True)
        assert resp.status_code == 200
        # Should redirect to dashboard
        assert b'Dashboard' in resp.data or resp.request.path == '/'

    def test_login_unapproved_user(self, client, db_session):
        from tests.conftest import _create_user
        _create_user(db_session, 'unapproved', 'password123', is_approved=False)
        resp = client.post('/auth/login', data={
            'username': 'unapproved',
            'password': 'password123',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'pending admin approval' in resp.data

    def test_login_wrong_password(self, client, auditor_user):
        resp = client.post('/auth/login', data={
            'username': 'testauditor',
            'password': 'wrongpass',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Invalid username or password' in resp.data

    def test_login_mfa_user_redirects_to_verify(self, client, db_session):
        from tests.conftest import _create_user
        user = _create_user(db_session, 'mfauser', 'password123')
        user.generate_mfa_secret()
        user.mfa_enabled = True
        db_session.session.commit()

        resp = client.post('/auth/login', data={
            'username': 'mfauser',
            'password': 'password123',
        })
        assert resp.status_code == 302
        assert '/auth/mfa-verify' in resp.headers['Location']


class TestMFA:
    def test_mfa_verify_valid_token(self, client, db_session):
        from tests.conftest import _create_user
        user = _create_user(db_session, 'mfauser', 'password123')
        secret = user.generate_mfa_secret()
        user.mfa_enabled = True
        db_session.session.commit()

        # Login to get to MFA stage
        client.post('/auth/login', data={
            'username': 'mfauser',
            'password': 'password123',
        })

        totp = pyotp.TOTP(secret)
        resp = client.post('/auth/mfa-verify', data={
            'token': totp.now(),
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_mfa_verify_invalid_token(self, client, db_session):
        from tests.conftest import _create_user
        user = _create_user(db_session, 'mfauser', 'password123')
        user.generate_mfa_secret()
        user.mfa_enabled = True
        db_session.session.commit()

        client.post('/auth/login', data={
            'username': 'mfauser',
            'password': 'password123',
        })

        resp = client.post('/auth/mfa-verify', data={
            'token': '000000',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Invalid verification code' in resp.data


class TestLogout:
    def test_logout(self, auth_client):
        resp = auth_client.post('/auth/logout', follow_redirects=True)
        assert resp.status_code == 200
        assert b'logged out' in resp.data


class TestProtectedRoutes:
    def test_unauthenticated_redirect(self, client, db_session):
        resp = client.get('/audits/')
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']
```

- [ ] **Step 2: Run tests**

Run: `cd /home/d3vn0mi/Desktop/opt/Kenbu-auditing-tool && python -m pytest tests/test_auth.py -v`
Expected: All 12 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_auth.py
git commit -m "Add authentication tests covering register, login, MFA, and logout"
```

---

### Task 3: Write benchmark browsing tests

**Files:**
- Create: `tests/test_benchmarks.py`

- [ ] **Step 1: Write tests/test_benchmarks.py**

```python
class TestBenchmarkBrowsing:
    def test_list_benchmarks(self, auth_client, seed_data):
        resp = auth_client.get('/benchmarks/')
        assert resp.status_code == 200
        assert b'Test CIS Benchmark' in resp.data

    def test_benchmark_detail(self, auth_client, seed_data):
        bid = seed_data['benchmark'].id
        resp = auth_client.get(f'/benchmarks/{bid}')
        assert resp.status_code == 200
        assert b'Test Section' in resp.data

    def test_section_detail(self, auth_client, seed_data):
        bid = seed_data['benchmark'].id
        sid = seed_data['section'].id
        resp = auth_client.get(f'/benchmarks/{bid}/section/{sid}')
        assert resp.status_code == 200
        assert b'Test Check 1.1' in resp.data

    def test_check_detail(self, auth_client, seed_data):
        check_id = seed_data['checks'][0].id
        resp = auth_client.get(f'/checks/{check_id}')
        assert resp.status_code == 200
        assert b'echo &quot;audit 1.1&quot;' in resp.data or b'audit 1.1' in resp.data
        assert b'Remediation for 1.1' in resp.data

    def test_search_by_keyword(self, auth_client, seed_data):
        resp = auth_client.get('/checks/search?q=Check+1.1')
        assert resp.status_code == 200
        assert b'Test Check 1.1' in resp.data

    def test_search_by_level(self, auth_client, seed_data):
        resp = auth_client.get('/checks/search?level=2')
        assert resp.status_code == 200
        # Only check 1.2 is L2
        assert b'Test Check 1.2' in resp.data
        assert b'Test Check 1.1' not in resp.data
```

- [ ] **Step 2: Run tests**

Run: `cd /home/d3vn0mi/Desktop/opt/Kenbu-auditing-tool && python -m pytest tests/test_benchmarks.py -v`
Expected: All 6 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_benchmarks.py
git commit -m "Add benchmark browsing and search tests"
```

---

### Task 4: Write audit session lifecycle tests

**Files:**
- Create: `tests/test_audits.py`

- [ ] **Step 1: Write tests/test_audits.py**

```python
import pytest
from app.models.audit import AuditSession, AuditAsset, AuditAssetBenchmark, AuditResult


def _create_audit(auth_client, title='Test Audit'):
    """Helper: create an audit session and return its ID from the redirect."""
    resp = auth_client.post('/audits/new', data={'title': title})
    assert resp.status_code == 302
    # Redirect goes to /audits/<id>
    return int(resp.headers['Location'].rstrip('/').split('/')[-1])


def _add_asset(auth_client, session_id, name='Server1', asset_type='linux'):
    """Helper: add an asset and return its ID."""
    resp = auth_client.post(f'/audits/{session_id}/assets/new', data={
        'name': name,
        'asset_type': asset_type,
    })
    assert resp.status_code == 302
    # Redirect goes to /audits/<sid>/assets/<aid>/benchmarks
    parts = resp.headers['Location'].rstrip('/').split('/')
    return int(parts[-2])  # asset_id


def _assign_benchmarks(auth_client, session_id, asset_id, benchmark_id):
    """Helper: assign a benchmark to an asset."""
    resp = auth_client.post(
        f'/audits/{session_id}/assets/{asset_id}/benchmarks',
        data={'benchmark_ids': benchmark_id},
    )
    assert resp.status_code == 302


def _start_audit(auth_client, session_id):
    """Helper: start an audit session."""
    resp = auth_client.post(f'/audits/{session_id}/start')
    assert resp.status_code == 302


class TestAuditList:
    def test_list_audits_empty(self, auth_client):
        resp = auth_client.get('/audits/')
        assert resp.status_code == 200


class TestAuditCreate:
    def test_create_audit(self, auth_client):
        sid = _create_audit(auth_client)
        session = AuditSession.query.get(sid)
        assert session is not None
        assert session.title == 'Test Audit'
        assert session.status == 'draft'

    def test_create_without_title(self, auth_client):
        resp = auth_client.post('/audits/new', data={'title': ''}, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Title is required' in resp.data


class TestAuditDetail:
    def test_view_session_detail(self, auth_client):
        sid = _create_audit(auth_client)
        resp = auth_client.get(f'/audits/{sid}')
        assert resp.status_code == 200
        assert b'Test Audit' in resp.data

    def test_edit_draft_session(self, auth_client):
        sid = _create_audit(auth_client)
        resp = auth_client.post(f'/audits/{sid}/edit', data={
            'title': 'Updated Title',
            'description': 'New description',
        }, follow_redirects=True)
        assert resp.status_code == 200
        session = AuditSession.query.get(sid)
        assert session.title == 'Updated Title'

    def test_edit_non_draft_session(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        resp = auth_client.post(f'/audits/{sid}/edit', data={
            'title': 'Should Not Change',
        }, follow_redirects=True)
        assert b'not in draft status' in resp.data


class TestAuditAssets:
    def test_add_asset(self, auth_client):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        asset = AuditAsset.query.get(aid)
        assert asset is not None
        assert asset.name == 'Server1'

    def test_assign_benchmarks(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        mappings = AuditAssetBenchmark.query.filter_by(asset_id=aid).all()
        assert len(mappings) == 1


class TestAuditLifecycle:
    def test_start_session(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        session = AuditSession.query.get(sid)
        assert session.status == 'in_progress'
        assert session.started_at is not None
        results = AuditResult.query.filter_by(asset_id=aid).all()
        assert len(results) == 3  # 3 checks in seed_data

    def test_start_without_assets(self, auth_client):
        sid = _create_audit(auth_client)
        resp = auth_client.post(f'/audits/{sid}/start', follow_redirects=True)
        assert b'at least one asset' in resp.data

    def test_start_with_unassigned_benchmarks(self, auth_client):
        sid = _create_audit(auth_client)
        _add_asset(auth_client, sid)
        resp = auth_client.post(f'/audits/{sid}/start', follow_redirects=True)
        assert b'no benchmarks assigned' in resp.data

    def test_update_single_result(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        check_id = seed_data['checks'][0].id
        resp = auth_client.post(
            f'/audits/{sid}/assets/{aid}/check/{check_id}',
            data={'status': 'pass', 'finding': 'Looks good'},
        )
        assert resp.status_code == 302
        result = AuditResult.query.filter_by(asset_id=aid, check_id=check_id).first()
        assert result.status == 'pass'
        assert result.finding == 'Looks good'
        assert result.checked_at is not None

    def test_bulk_update_results(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        check_ids = [c.id for c in seed_data['checks']]
        resp = auth_client.post(
            f'/audits/{sid}/assets/{aid}/bulk-update',
            data={'bulk_status': 'pass', 'check_ids': check_ids},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        for cid in check_ids:
            result = AuditResult.query.filter_by(asset_id=aid, check_id=cid).first()
            assert result.status == 'pass'

    def test_complete_session(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        resp = auth_client.post(f'/audits/{sid}/complete')
        assert resp.status_code == 302
        session = AuditSession.query.get(sid)
        assert session.status == 'completed'
        assert session.completed_at is not None


class TestAuditDelete:
    def test_delete_draft_session(self, auth_client):
        sid = _create_audit(auth_client)
        resp = auth_client.post(f'/audits/{sid}/delete', follow_redirects=True)
        assert resp.status_code == 200
        assert AuditSession.query.get(sid) is None

    def test_delete_non_draft_session(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        resp = auth_client.post(f'/audits/{sid}/delete', follow_redirects=True)
        assert b'not in draft status' in resp.data
        assert AuditSession.query.get(sid) is not None


class TestAuditAccessControl:
    def test_access_other_users_session(self, app, db_session, seed_data):
        """A second user cannot access the first user's audit session."""
        from tests.conftest import _create_user, _login

        # Create two users
        _create_user(db_session, 'user_a', 'password123', role='auditor')
        _create_user(db_session, 'user_b', 'password123', role='auditor')

        client_a = app.test_client()
        _login(client_a, 'user_a', 'password123')
        sid = _create_audit(client_a, title='Private Audit')

        client_b = app.test_client()
        _login(client_b, 'user_b', 'password123')
        resp = client_b.get(f'/audits/{sid}')
        assert resp.status_code == 403
```

- [ ] **Step 2: Run tests**

Run: `cd /home/d3vn0mi/Desktop/opt/Kenbu-auditing-tool && python -m pytest tests/test_audits.py -v`
Expected: All 17 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_audits.py
git commit -m "Add audit session lifecycle tests"
```

---

### Task 5: Write hardening task lifecycle tests

**Files:**
- Create: `tests/test_hardening.py`

- [ ] **Step 1: Write tests/test_hardening.py**

```python
import pytest
from app.models.hardening import HardeningTask, HardeningAsset, HardeningAssetBenchmark, HardeningCheckResult


def _create_task(auth_client, title='Test Hardening'):
    resp = auth_client.post('/hardening/new', data={'title': title})
    assert resp.status_code == 302
    return int(resp.headers['Location'].rstrip('/').split('/')[-1])


def _add_asset(auth_client, task_id, name='Server1', asset_type='linux'):
    resp = auth_client.post(f'/hardening/{task_id}/assets/new', data={
        'name': name,
        'asset_type': asset_type,
    })
    assert resp.status_code == 302
    parts = resp.headers['Location'].rstrip('/').split('/')
    return int(parts[-2])  # asset_id


def _assign_benchmarks(auth_client, task_id, asset_id, benchmark_id):
    resp = auth_client.post(
        f'/hardening/{task_id}/assets/{asset_id}/benchmarks',
        data={'benchmark_ids': benchmark_id},
    )
    assert resp.status_code == 302


def _start_task(auth_client, task_id):
    resp = auth_client.post(f'/hardening/{task_id}/start')
    assert resp.status_code == 302


class TestHardeningList:
    def test_list_tasks_empty(self, auth_client):
        resp = auth_client.get('/hardening/')
        assert resp.status_code == 200


class TestHardeningCreate:
    def test_create_task(self, auth_client):
        tid = _create_task(auth_client)
        task = HardeningTask.query.get(tid)
        assert task is not None
        assert task.title == 'Test Hardening'
        assert task.status == 'draft'

    def test_create_without_title(self, auth_client):
        resp = auth_client.post('/hardening/new', data={'title': ''}, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Title is required' in resp.data


class TestHardeningAssets:
    def test_add_asset(self, auth_client):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        asset = HardeningAsset.query.get(aid)
        assert asset is not None
        assert asset.name == 'Server1'

    def test_assign_benchmarks(self, auth_client, seed_data):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        _assign_benchmarks(auth_client, tid, aid, seed_data['benchmark'].id)
        mappings = HardeningAssetBenchmark.query.filter_by(asset_id=aid).all()
        assert len(mappings) == 1


class TestHardeningLifecycle:
    def test_start_task(self, auth_client, seed_data):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        _assign_benchmarks(auth_client, tid, aid, seed_data['benchmark'].id)
        _start_task(auth_client, tid)

        task = HardeningTask.query.get(tid)
        assert task.status == 'in_progress'
        assert task.started_at is not None
        results = HardeningCheckResult.query.filter_by(asset_id=aid).all()
        assert len(results) == 3

    def test_start_without_assets(self, auth_client):
        tid = _create_task(auth_client)
        resp = auth_client.post(f'/hardening/{tid}/start', follow_redirects=True)
        assert b'at least one asset' in resp.data

    def test_update_single_check(self, auth_client, seed_data):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        _assign_benchmarks(auth_client, tid, aid, seed_data['benchmark'].id)
        _start_task(auth_client, tid)

        check_id = seed_data['checks'][0].id
        resp = auth_client.post(
            f'/hardening/{tid}/assets/{aid}/check/{check_id}',
            data={'status': 'done', 'notes': 'Applied fix'},
        )
        assert resp.status_code == 302
        result = HardeningCheckResult.query.filter_by(asset_id=aid, check_id=check_id).first()
        assert result.status == 'done'
        assert result.notes == 'Applied fix'

    def test_bulk_update_checks(self, auth_client, seed_data):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        _assign_benchmarks(auth_client, tid, aid, seed_data['benchmark'].id)
        _start_task(auth_client, tid)

        check_ids = [c.id for c in seed_data['checks']]
        resp = auth_client.post(
            f'/hardening/{tid}/assets/{aid}/bulk-update',
            data={'bulk_status': 'done', 'check_ids': check_ids},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        for cid in check_ids:
            result = HardeningCheckResult.query.filter_by(asset_id=aid, check_id=cid).first()
            assert result.status == 'done'

    def test_complete_task(self, auth_client, seed_data):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        _assign_benchmarks(auth_client, tid, aid, seed_data['benchmark'].id)
        _start_task(auth_client, tid)

        resp = auth_client.post(f'/hardening/{tid}/complete')
        assert resp.status_code == 302
        task = HardeningTask.query.get(tid)
        assert task.status == 'completed'


class TestHardeningDelete:
    def test_delete_draft_task(self, auth_client):
        tid = _create_task(auth_client)
        resp = auth_client.post(f'/hardening/{tid}/delete', follow_redirects=True)
        assert resp.status_code == 200
        assert HardeningTask.query.get(tid) is None


class TestHardeningAccessControl:
    def test_access_other_users_task(self, app, db_session, seed_data):
        from tests.conftest import _create_user, _login

        _create_user(db_session, 'harden_a', 'password123', role='auditor')
        _create_user(db_session, 'harden_b', 'password123', role='auditor')

        client_a = app.test_client()
        _login(client_a, 'harden_a', 'password123')
        tid = _create_task(client_a)

        client_b = app.test_client()
        _login(client_b, 'harden_b', 'password123')
        resp = client_b.get(f'/hardening/{tid}')
        assert resp.status_code == 403
```

- [ ] **Step 2: Run tests**

Run: `cd /home/d3vn0mi/Desktop/opt/Kenbu-auditing-tool && python -m pytest tests/test_hardening.py -v`
Expected: All 13 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_hardening.py
git commit -m "Add hardening task lifecycle tests"
```

---

### Task 6: Write pentest assessment lifecycle tests

**Files:**
- Create: `tests/test_pentests.py`

- [ ] **Step 1: Write tests/test_pentests.py**

```python
import pytest
from app.models.pentest import (
    PentestAssessment, PentestPhase, PentestChecklistItem,
    PentestFinding, PentestTeamMember, ASSESSMENT_TYPES, SEVERITY_LEVELS, TEAM_ROLES,
)


def _create_assessment(auth_client, title='Test Pentest'):
    resp = auth_client.post('/pentests/new', data={
        'title': title,
        'client_name': 'Test Client',
        'assessment_type': 'network',
        'scope_description': 'Test scope',
    })
    assert resp.status_code == 302
    return int(resp.headers['Location'].rstrip('/').split('/')[-1])


class TestPentestList:
    def test_list_assessments_empty(self, auth_client):
        resp = auth_client.get('/pentests/')
        assert resp.status_code == 200


class TestPentestCreate:
    def test_create_assessment(self, auth_client):
        aid = _create_assessment(auth_client)
        assessment = PentestAssessment.query.get(aid)
        assert assessment is not None
        assert assessment.title == 'Test Pentest'
        assert assessment.status == 'setup'
        # Phases should be auto-created
        phases = assessment.phases.all()
        assert len(phases) > 0

    def test_view_detail(self, auth_client):
        aid = _create_assessment(auth_client)
        resp = auth_client.get(f'/pentests/{aid}')
        assert resp.status_code == 200
        assert b'Test Pentest' in resp.data


class TestPentestLifecycle:
    def test_start_assessment(self, auth_client):
        aid = _create_assessment(auth_client)
        resp = auth_client.post(f'/pentests/{aid}/start')
        assert resp.status_code == 302
        assessment = PentestAssessment.query.get(aid)
        assert assessment.status == 'in_progress'
        # First phase should be auto-started
        first_phase = assessment.phases.order_by(PentestPhase.phase_order).first()
        assert first_phase.status == 'in_progress'

    def test_complete_assessment(self, auth_client):
        aid = _create_assessment(auth_client)
        auth_client.post(f'/pentests/{aid}/start')
        resp = auth_client.post(f'/pentests/{aid}/complete')
        assert resp.status_code == 302
        assessment = PentestAssessment.query.get(aid)
        assert assessment.status == 'completed'

    def test_delete_setup_assessment(self, auth_client):
        aid = _create_assessment(auth_client)
        resp = auth_client.post(f'/pentests/{aid}/delete', follow_redirects=True)
        assert resp.status_code == 200
        assert PentestAssessment.query.get(aid) is None


class TestPhaseManagement:
    def test_view_phase_detail(self, auth_client):
        aid = _create_assessment(auth_client)
        assessment = PentestAssessment.query.get(aid)
        phase = assessment.phases.first()
        resp = auth_client.get(f'/pentests/{aid}/phases/{phase.id}')
        assert resp.status_code == 200

    def test_start_phase(self, auth_client):
        aid = _create_assessment(auth_client)
        assessment = PentestAssessment.query.get(aid)
        phase = assessment.phases.first()
        resp = auth_client.post(f'/pentests/{aid}/phases/{phase.id}/start')
        assert resp.status_code == 302
        phase = PentestPhase.query.get(phase.id)
        assert phase.status == 'in_progress'

    def test_complete_phase(self, auth_client):
        aid = _create_assessment(auth_client)
        assessment = PentestAssessment.query.get(aid)
        phase = assessment.phases.first()
        auth_client.post(f'/pentests/{aid}/phases/{phase.id}/start')
        resp = auth_client.post(f'/pentests/{aid}/phases/{phase.id}/complete')
        assert resp.status_code == 302
        phase = PentestPhase.query.get(phase.id)
        assert phase.status == 'completed'

    def test_skip_phase(self, auth_client):
        aid = _create_assessment(auth_client)
        assessment = PentestAssessment.query.get(aid)
        phase = assessment.phases.first()
        resp = auth_client.post(f'/pentests/{aid}/phases/{phase.id}/skip')
        assert resp.status_code == 302
        phase = PentestPhase.query.get(phase.id)
        assert phase.status == 'skipped'


class TestChecklistItems:
    def test_toggle_checklist_item(self, auth_client):
        aid = _create_assessment(auth_client)
        assessment = PentestAssessment.query.get(aid)
        phase = assessment.phases.first()
        item = phase.checklist_items.first()
        assert item.is_completed is False

        resp = auth_client.post(
            f'/pentests/{aid}/phases/{phase.id}/items/{item.id}/toggle',
        )
        assert resp.status_code == 302
        item = PentestChecklistItem.query.get(item.id)
        assert item.is_completed is True

    def test_add_checklist_item(self, auth_client):
        aid = _create_assessment(auth_client)
        assessment = PentestAssessment.query.get(aid)
        phase = assessment.phases.first()
        original_count = phase.checklist_items.count()

        resp = auth_client.post(
            f'/pentests/{aid}/phases/{phase.id}/items/add',
            data={'title': 'Custom checklist item'},
        )
        assert resp.status_code == 302
        assert phase.checklist_items.count() == original_count + 1


class TestFindings:
    def test_create_finding(self, auth_client):
        aid = _create_assessment(auth_client)
        resp = auth_client.post(f'/pentests/{aid}/findings/new', data={
            'title': 'SQL Injection',
            'severity': 'critical',
            'description': 'Found SQLi in login form',
        })
        assert resp.status_code == 302
        findings = PentestFinding.query.filter_by(assessment_id=aid).all()
        assert len(findings) == 1
        assert findings[0].title == 'SQL Injection'
        assert findings[0].severity == 'critical'

    def test_edit_finding(self, auth_client):
        aid = _create_assessment(auth_client)
        auth_client.post(f'/pentests/{aid}/findings/new', data={
            'title': 'XSS',
            'severity': 'high',
        })
        finding = PentestFinding.query.filter_by(assessment_id=aid).first()
        resp = auth_client.post(
            f'/pentests/{aid}/findings/{finding.id}/edit',
            data={'title': 'Stored XSS', 'severity': 'critical'},
        )
        assert resp.status_code == 302
        finding = PentestFinding.query.get(finding.id)
        assert finding.title == 'Stored XSS'
        assert finding.severity == 'critical'

    def test_delete_finding(self, auth_client):
        aid = _create_assessment(auth_client)
        auth_client.post(f'/pentests/{aid}/findings/new', data={
            'title': 'To Delete',
            'severity': 'low',
        })
        finding = PentestFinding.query.filter_by(assessment_id=aid).first()
        resp = auth_client.post(f'/pentests/{aid}/findings/{finding.id}/delete')
        assert resp.status_code == 302
        assert PentestFinding.query.get(finding.id) is None


class TestTeamManagement:
    def test_add_team_member(self, auth_client, db_session):
        from tests.conftest import _create_user
        _create_user(db_session, 'teammate', 'password123', role='auditor')

        aid = _create_assessment(auth_client)
        resp = auth_client.post(f'/pentests/{aid}/team/add', data={
            'username': 'teammate',
            'role': 'tester',
        }, follow_redirects=True)
        assert resp.status_code == 200
        members = PentestTeamMember.query.filter_by(assessment_id=aid).all()
        assert len(members) == 1
        assert members[0].role == 'tester'

    def test_remove_team_member(self, auth_client, db_session):
        from tests.conftest import _create_user
        _create_user(db_session, 'removeme', 'password123', role='auditor')

        aid = _create_assessment(auth_client)
        auth_client.post(f'/pentests/{aid}/team/add', data={
            'username': 'removeme',
            'role': 'observer',
        })
        member = PentestTeamMember.query.filter_by(assessment_id=aid).first()
        resp = auth_client.post(f'/pentests/{aid}/team/{member.id}/remove')
        assert resp.status_code == 302
        assert PentestTeamMember.query.get(member.id) is None
```

- [ ] **Step 2: Run tests**

Run: `cd /home/d3vn0mi/Desktop/opt/Kenbu-auditing-tool && python -m pytest tests/test_pentests.py -v`
Expected: All 15 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_pentests.py
git commit -m "Add pentest assessment lifecycle tests"
```

---

### Task 7: Write export tests

**Files:**
- Create: `tests/test_export.py`

- [ ] **Step 1: Write tests/test_export.py**

```python
import pytest
from app.models.audit import AuditSession, AuditAsset, AuditAssetBenchmark, AuditResult
from app.models.hardening import HardeningTask, HardeningAsset, HardeningAssetBenchmark, HardeningCheckResult

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class TestBenchmarkExport:
    def test_export_benchmark(self, auth_client, seed_data):
        bid = seed_data['benchmark'].id
        resp = auth_client.get(f'/export/benchmark/{bid}')
        assert resp.status_code == 200
        assert resp.content_type == XLSX_MIME
        assert len(resp.data) > 0


class TestAuditExport:
    def test_export_audit(self, auth_client, seed_data, auditor_user):
        # Create a started audit session with results
        session = AuditSession(
            user_id=auditor_user.id,
            title='Export Test Audit',
            status='in_progress',
        )
        from app.extensions import db
        db.session.add(session)
        db.session.flush()

        asset = AuditAsset(
            session_id=session.id,
            name='TestServer',
            asset_type='linux',
        )
        db.session.add(asset)
        db.session.flush()

        AuditAssetBenchmark(asset_id=asset.id, benchmark_id=seed_data['benchmark'].id)
        for check in seed_data['checks']:
            result = AuditResult(asset_id=asset.id, check_id=check.id, status='pass')
            db.session.add(result)
        db.session.commit()

        resp = auth_client.get(f'/export/audit/{session.id}')
        assert resp.status_code == 200
        assert resp.content_type == XLSX_MIME
        assert len(resp.data) > 0


class TestHardeningExport:
    def test_export_hardening_excel(self, auth_client, seed_data, auditor_user):
        from app.extensions import db

        task = HardeningTask(
            user_id=auditor_user.id,
            title='Export Test Hardening',
            status='in_progress',
        )
        db.session.add(task)
        db.session.flush()

        asset = HardeningAsset(
            task_id=task.id,
            name='TestServer',
            asset_type='linux',
        )
        db.session.add(asset)
        db.session.flush()

        for check in seed_data['checks']:
            result = HardeningCheckResult(asset_id=asset.id, check_id=check.id, status='done')
            db.session.add(result)
        db.session.commit()

        resp = auth_client.get(f'/export/hardening/{task.id}/excel')
        assert resp.status_code == 200
        assert resp.content_type == XLSX_MIME
        assert len(resp.data) > 0
```

- [ ] **Step 2: Run tests**

Run: `cd /home/d3vn0mi/Desktop/opt/Kenbu-auditing-tool && python -m pytest tests/test_export.py -v`
Expected: All 3 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_export.py
git commit -m "Add Excel export tests"
```

---

### Task 8: Write seed tests

**Files:**
- Create: `tests/test_seed.py`

- [ ] **Step 1: Write tests/test_seed.py**

```python
import os
import pytest
from app.models import Platform, Benchmark, BenchmarkSection, Check
from app.utils.seed import seed_platforms, seed_benchmark_file, seed_all

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
BENCHMARKS_DIR = os.path.join(DATA_DIR, 'benchmarks')


class TestSeedPlatforms:
    def test_seed_platforms_creates_expected_count(self, db_session):
        seed_platforms()
        count = Platform.query.count()
        assert count == 15


class TestSeedBenchmark:
    def test_seed_single_benchmark_file(self, db_session):
        # Seed platforms first (benchmark references platform slug)
        seed_platforms()

        filepath = os.path.join(BENCHMARKS_DIR, 'hp_ilo_5.yaml')
        assert os.path.exists(filepath), f'Test YAML not found: {filepath}'
        seed_benchmark_file(filepath)

        benchmarks = Benchmark.query.all()
        assert len(benchmarks) == 1
        bm = benchmarks[0]
        assert bm.platform is not None

        # Verify hierarchical structure
        sections = BenchmarkSection.query.filter_by(benchmark_id=bm.id).all()
        assert len(sections) > 0
        checks = Check.query.join(BenchmarkSection).filter(
            BenchmarkSection.benchmark_id == bm.id
        ).all()
        assert len(checks) > 0

        # Verify parent-child exists
        child_sections = [s for s in sections if s.parent_id is not None]
        assert len(child_sections) > 0


class TestSeedAll:
    def test_seed_all(self, db_session):
        seed_all(DATA_DIR)
        assert Platform.query.count() > 0
        assert Benchmark.query.count() > 0
        assert BenchmarkSection.query.count() > 0
        assert Check.query.count() > 0
```

- [ ] **Step 2: Run tests**

Run: `cd /home/d3vn0mi/Desktop/opt/Kenbu-auditing-tool && python -m pytest tests/test_seed.py -v`
Expected: All 3 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_seed.py
git commit -m "Add data seeding tests"
```

---

### Task 9: Run full suite, verify coverage, final commit

**Files:**
- No new files

- [ ] **Step 1: Run the full test suite**

Run: `cd /home/d3vn0mi/Desktop/opt/Kenbu-auditing-tool && python -m pytest tests/ -v`
Expected: All ~67 tests PASS

- [ ] **Step 2: Run with coverage report**

Run: `cd /home/d3vn0mi/Desktop/opt/Kenbu-auditing-tool && python -m pytest tests/ -v --cov=app --cov-report=term-missing`
Expected: Coverage report showing route coverage. No specific % target, but auth, audits, hardening, pentests, export routes should show significant coverage.

- [ ] **Step 3: Fix any failing tests**

If any tests fail, diagnose and fix them. Common issues:
- Template rendering errors from missing context variables: check what the template expects and provide it in fixture data
- Redirect URL parsing: adjust URL parsing in helper functions
- HTMX partial template issues: the test client doesn't send HX-Request header by default, so routes should take the non-HTMX path (redirect)

- [ ] **Step 4: Final commit if fixes were needed**

```bash
git add -A tests/
git commit -m "Fix test issues found during full suite run"
```
