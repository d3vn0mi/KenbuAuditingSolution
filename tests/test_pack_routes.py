"""Tests for the readiness pack export routes (Phase 3)."""
from app.models import Regulation, Control, ReadinessAssessment, ControlStatus


def _assessment(db_session):
    reg = Regulation(name='NIS2', short_code='NIS2', slug='nis2', status='in_force')
    db_session.session.add(reg)
    db_session.session.flush()
    control = Control(code='SC-01', title='Supply-chain RM', domain='SupplyChain')
    db_session.session.add(control)
    db_session.session.flush()
    a = ReadinessAssessment(title='Q2', regulation_id=reg.id, status='active')
    db_session.session.add(a)
    db_session.session.flush()
    db_session.session.add(ControlStatus(assessment_id=a.id, control_id=control.id,
                                         status='implemented'))
    db_session.session.commit()
    return a


def test_export_excel_route(auth_client, db_session):
    a = _assessment(db_session)
    resp = auth_client.get(f'/readiness/{a.id}/export.xlsx')
    assert resp.status_code == 200
    assert resp.data[:2] == b'PK'
    assert 'spreadsheet' in resp.headers['Content-Type']


def test_export_pdf_route(auth_client, db_session):
    a = _assessment(db_session)
    resp = auth_client.get(f'/readiness/{a.id}/export.pdf')
    assert resp.status_code == 200
    assert resp.data[:5] == b'%PDF-'
    assert resp.headers['Content-Type'] == 'application/pdf'


def test_export_requires_compliance(app, client, db_session):
    from tests.conftest import _create_user, _login
    a = _assessment(db_session)
    _create_user(db_session, 'eng', 'password123', role='security_engineer')
    _login(client, 'eng', 'password123')
    assert client.get(f'/readiness/{a.id}/export.pdf').status_code == 403
