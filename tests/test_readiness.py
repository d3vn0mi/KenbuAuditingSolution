"""Tests for readiness assessment, scoring and remediation roadmap (Phase 2)."""
from app.models import (
    Regulation, Obligation, Control, ReadinessAssessment, ControlStatus,
)
from app.utils import readiness


def _control(db_session, code, domain='IAM', obligations=None):
    c = Control(code=code, title=code, domain=domain)
    if obligations:
        c.obligations.extend(obligations)
    db_session.session.add(c)
    db_session.session.flush()
    return c


def _assessment(db_session, regulation_id=None):
    a = ReadinessAssessment(title='Q2 readiness', regulation_id=regulation_id)
    db_session.session.add(a)
    db_session.session.flush()
    return a


def _set_status(db_session, assessment, control, status, maturity=None):
    cs = ControlStatus(assessment_id=assessment.id, control_id=control.id,
                       status=status, maturity=maturity)
    db_session.session.add(cs)
    db_session.session.flush()
    return cs


def test_assessment_score_excludes_not_applicable(db_session):
    a = _assessment(db_session)
    c1 = _control(db_session, 'C1')
    c2 = _control(db_session, 'C2')
    c3 = _control(db_session, 'C3')
    c4 = _control(db_session, 'C4')
    _set_status(db_session, a, c1, 'implemented')      # 1.0
    _set_status(db_session, a, c2, 'partial')          # 0.5
    _set_status(db_session, a, c3, 'not_started')      # 0.0
    _set_status(db_session, a, c4, 'not_applicable')   # excluded
    db_session.session.commit()

    # (1.0 + 0.5 + 0.0) / 3 = 0.5
    assert abs(readiness.assessment_score(a) - 0.5) < 1e-9


def test_domain_scores_group_by_domain(db_session):
    a = _assessment(db_session)
    c1 = _control(db_session, 'C1', domain='IAM')
    c2 = _control(db_session, 'C2', domain='IAM')
    c3 = _control(db_session, 'C3', domain='Crypto')
    _set_status(db_session, a, c1, 'implemented')
    _set_status(db_session, a, c2, 'not_started')
    _set_status(db_session, a, c3, 'implemented')
    db_session.session.commit()

    scores = readiness.domain_scores(a)
    assert abs(scores['IAM'] - 0.5) < 1e-9
    assert abs(scores['Crypto'] - 1.0) < 1e-9


def test_obligation_coverage(db_session):
    reg = Regulation(name='NIS2', short_code='NIS2', slug='nis2', status='in_force')
    db_session.session.add(reg)
    db_session.session.flush()
    ob1 = Obligation(regulation_id=reg.id, ref='Art.1', title='one')
    ob2 = Obligation(regulation_id=reg.id, ref='Art.2', title='two')
    db_session.session.add_all([ob1, ob2])
    db_session.session.flush()
    a = _assessment(db_session, regulation_id=reg.id)
    c1 = _control(db_session, 'C1', obligations=[ob1])
    c2 = _control(db_session, 'C2', obligations=[ob2])
    _set_status(db_session, a, c1, 'implemented')
    _set_status(db_session, a, c2, 'partial')
    db_session.session.commit()

    cov = readiness.obligation_coverage(a, reg)
    assert cov['total'] == 2
    assert cov['covered'] == 1          # only ob1 has an implemented control
    assert abs(cov['ratio'] - 0.5) < 1e-9


def test_remediation_roadmap_ranks_by_impact(db_session):
    reg = Regulation(name='NIS2', short_code='NIS2', slug='nis2', status='in_force')
    db_session.session.add(reg)
    db_session.session.flush()
    obs = [Obligation(regulation_id=reg.id, ref=f'Art.{i}', title=str(i)) for i in range(3)]
    db_session.session.add_all(obs)
    db_session.session.flush()
    a = _assessment(db_session, regulation_id=reg.id)
    high = _control(db_session, 'HIGH', obligations=obs)        # maps 3 obligations
    low = _control(db_session, 'LOW', obligations=[obs[0]])     # maps 1 obligation
    done = _control(db_session, 'DONE', obligations=[obs[0]])
    _set_status(db_session, a, high, 'not_started', maturity=0)
    _set_status(db_session, a, low, 'partial', maturity=2)
    _set_status(db_session, a, done, 'implemented')
    db_session.session.commit()

    roadmap = readiness.remediation_roadmap(a)
    codes = [item['control'].code for item in roadmap]
    assert 'DONE' not in codes              # implemented controls are not gaps
    assert codes[0] == 'HIGH'               # highest impact first
    assert set(codes) == {'HIGH', 'LOW'}
