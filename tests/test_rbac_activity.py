"""Tests for RBAC (viewer read-only) + activity log (Phase 4 m10)."""
from app.models import Regulation, Control, ReadinessAssessment, ActivityLog
from tests.conftest import _create_user, _login


def test_viewer_can_read_but_not_write(app, client, db_session):
    reg = Regulation(name='NIS2', short_code='NIS2', slug='nis2', status='in_force')
    db_session.session.add(reg)
    db_session.session.commit()
    _create_user(db_session, 'view1', 'password123', role='viewer')
    _login(client, 'view1', 'password123')

    # read-only access to the compliance layer
    assert client.get('/readiness/').status_code == 200
    assert client.get('/evidence/').status_code == 200
    assert client.get('/findings/').status_code == 200
    # but cannot create (write is compliance_required)
    assert client.get('/readiness/new').status_code == 403
    assert client.post('/readiness/new', data={'title': 'x'}).status_code == 403


def test_lead_auditor_can_write(app, client, db_session):
    _create_user(db_session, 'lead1', 'password123', role='lead_auditor')
    _login(client, 'lead1', 'password123')
    resp = client.post('/readiness/new', data={'title': 'Lead assessment'},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert ReadinessAssessment.query.filter_by(title='Lead assessment').count() == 1


def test_activity_log_records_mutation(app, client, db_session):
    _create_user(db_session, 'aud1', 'password123', role='auditor')
    _login(client, 'aud1', 'password123')
    client.post('/readiness/new', data={'title': 'Logged assessment'},
                follow_redirects=True)

    entry = ActivityLog.query.filter_by(endpoint='readiness.new_assessment').first()
    assert entry is not None
    assert entry.username == 'aud1'
    assert entry.method == 'POST'


def test_only_admin_sees_activity(app, client, db_session):
    _create_user(db_session, 'aud2', 'password123', role='auditor')
    _login(client, 'aud2', 'password123')
    assert client.get('/admin/activity').status_code == 403
