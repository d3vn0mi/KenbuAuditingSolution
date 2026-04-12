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
