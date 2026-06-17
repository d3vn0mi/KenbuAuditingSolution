"""Tests for the findings UI routes (Phase 2 m7)."""
import io
import json

from app.models import Control, Finding
from app.models.pentest import PentestAssessment, PentestFinding
from tests.conftest import _create_user, _login


def test_findings_requires_compliance(app, client, db_session):
    _create_user(db_session, 'eng', 'password123', role='security_engineer')
    _login(client, 'eng', 'password123')
    assert client.get('/findings/').status_code == 403


def test_new_finding_links_control(auth_client, db_session):
    control = Control(code='IAM-01', title='Access control', domain='IAM')
    db_session.session.add(control)
    db_session.session.commit()

    resp = auth_client.post('/findings/new', data={
        'title': 'Weak SSH config', 'severity': 'high', 'source': 'tlpt',
        'control_ids': str(control.id),
    }, follow_redirects=True)
    assert resp.status_code == 200
    f = Finding.query.filter_by(title='Weak SSH config').one()
    assert f.controls[0].code == 'IAM-01'
    assert f.status == 'open'


def test_import_findings_json(auth_client, db_session):
    Control_ = Control(code='SC-01', title='Supply chain', domain='SupplyChain')
    db_session.session.add(Control_)
    db_session.session.commit()

    payload = json.dumps([
        {'title': 'Imported A', 'severity': 'critical', 'source': 'scan',
         'controls': ['SC-01']},
    ])
    resp = auth_client.post('/findings/import', data={
        'file': (io.BytesIO(payload.encode()), 'findings.json'),
    }, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200
    f = Finding.query.filter_by(title='Imported A').one()
    assert f.severity == 'critical'
    assert f.controls[0].code == 'SC-01'


def test_promote_pentest_finding(auth_client, db_session):
    user = _create_user(db_session, 'lead', 'password123', role='auditor')
    pa = PentestAssessment(user_id=user.id, title='Engagement', client_name='ACME',
                           assessment_type='network')
    db_session.session.add(pa)
    db_session.session.flush()
    pf = PentestFinding(assessment_id=pa.id, title='RCE on relay', severity='critical')
    db_session.session.add(pf)
    db_session.session.commit()

    resp = auth_client.post(f'/findings/promote/{pf.id}', follow_redirects=True)
    assert resp.status_code == 200
    f = Finding.query.filter_by(promoted_from_pentest_finding_id=pf.id).one()
    assert f.title == 'RCE on relay'
    assert f.source == 'pentest'
