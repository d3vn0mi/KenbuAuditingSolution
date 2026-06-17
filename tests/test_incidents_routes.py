"""Tests for the incident workflow routes (Phase 4 m8)."""
from app.models import Incident
from tests.conftest import _create_user, _login


def test_incidents_requires_compliance(app, client, db_session):
    _create_user(db_session, 'eng', 'password123', role='security_engineer')
    _login(client, 'eng', 'password123')
    assert client.get('/incidents/').status_code == 403


def test_new_incident_starts_clock(auth_client, db_session):
    resp = auth_client.post('/incidents/new', data={
        'title': 'Ground station breach', 'severity': 'critical',
        'detected_at': '2026-06-01T12:00',
    }, follow_redirects=True)
    assert resp.status_code == 200
    i = Incident.query.filter_by(title='Ground station breach').one()
    assert i.detected_at.year == 2026
    # detail page shows the three statutory stages
    detail = auth_client.get(f'/incidents/{i.id}')
    assert b'Early warning (24h)' in detail.data
    assert b'Final report (1 month)' in detail.data


def test_mark_stage_sent(auth_client, db_session):
    auth_client.post('/incidents/new', data={
        'title': 'X', 'severity': 'high', 'detected_at': '2026-06-01T12:00',
    }, follow_redirects=True)
    i = Incident.query.filter_by(title='X').one()
    auth_client.post(f'/incidents/{i.id}/stage/early_warning/sent', follow_redirects=True)
    refreshed = db_session.session.get(Incident, i.id)
    assert refreshed.early_warning_sent_at is not None


def test_report_template_renders(auth_client, db_session):
    auth_client.post('/incidents/new', data={
        'title': 'Y', 'severity': 'high', 'detected_at': '2026-06-01T12:00',
    }, follow_redirects=True)
    i = Incident.query.filter_by(title='Y').one()
    resp = auth_client.get(f'/incidents/{i.id}/report/notification')
    assert resp.status_code == 200
    assert b'Art. 23(4)(b)' in resp.data
