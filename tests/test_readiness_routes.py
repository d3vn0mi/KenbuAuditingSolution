"""Tests for the readiness UI routes (Phase 2)."""
from app.models import (
    Regulation, Obligation, Control, ReadinessAssessment, ControlStatus,
)
from tests.conftest import _create_user, _login


def _seed_reg_with_control(db_session):
    reg = Regulation(name='NIS2', short_code='NIS2', slug='nis2', status='in_force')
    db_session.session.add(reg)
    db_session.session.flush()
    ob = Obligation(regulation_id=reg.id, ref='Art.21(2)(d)', title='Supply chain')
    db_session.session.add(ob)
    db_session.session.flush()
    control = Control(code='SC-01', title='Supply-chain RM', domain='SupplyChain')
    control.obligations.append(ob)
    db_session.session.add(control)
    db_session.session.commit()
    return reg, ob, control


def test_readiness_requires_compliance_permission(app, client, db_session):
    # security_engineer lacks the 'compliance' feature
    _create_user(db_session, 'eng', 'password123', role='security_engineer')
    _login(client, 'eng', 'password123')
    assert client.get('/readiness/').status_code == 403


def test_new_assessment_populates_control_statuses(auth_client, db_session):
    reg, ob, control = _seed_reg_with_control(db_session)
    resp = auth_client.post('/readiness/new', data={
        'title': 'Q2 NIS2', 'regulation_id': reg.id,
    }, follow_redirects=True)
    assert resp.status_code == 200
    a = ReadinessAssessment.query.filter_by(title='Q2 NIS2').one()
    statuses = a.control_statuses.all()
    assert len(statuses) == 1
    assert statuses[0].control_id == control.id
    assert statuses[0].status == 'not_started'


def test_assessment_detail_renders_score(auth_client, db_session):
    reg, ob, control = _seed_reg_with_control(db_session)
    a = ReadinessAssessment(title='A', regulation_id=reg.id, status='active')
    db_session.session.add(a)
    db_session.session.flush()
    db_session.session.add(ControlStatus(assessment_id=a.id, control_id=control.id,
                                         status='implemented'))
    db_session.session.commit()

    resp = auth_client.get(f'/readiness/{a.id}')
    assert resp.status_code == 200
    assert b'SC-01' in resp.data
    assert b'100%' in resp.data  # single implemented control => 100%


def test_update_control_status_via_htmx(auth_client, db_session):
    reg, ob, control = _seed_reg_with_control(db_session)
    a = ReadinessAssessment(title='A', regulation_id=reg.id, status='active')
    db_session.session.add(a)
    db_session.session.flush()
    cs = ControlStatus(assessment_id=a.id, control_id=control.id, status='not_started')
    db_session.session.add(cs)
    db_session.session.commit()

    resp = auth_client.post(
        f'/readiness/{a.id}/control/{control.id}',
        data={'status': 'implemented', 'maturity': '4'},
        headers={'HX-Request': 'true'},
    )
    assert resp.status_code == 200
    assert b'cs-row-' in resp.data           # row partial returned
    assert b'score-summary' in resp.data     # OOB summary returned
    refreshed = db_session.session.get(ControlStatus, cs.id)
    assert refreshed.status == 'implemented'
    assert refreshed.maturity == 4
