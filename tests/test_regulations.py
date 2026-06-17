"""Tests for the regulatory layer (Phase 1)."""
from datetime import date

from app.extensions import db
from app.models import Regulation, RegulationCheck, AuditSession, Check


def test_regulation_has_readiness_fields(db_session):
    """Regulation carries short_code, status, effective_date and source_url."""
    reg = Regulation(
        name='Network and Information Security Directive (EU) 2022/2555',
        short_code='NIS2',
        slug='nis2',
        version='2022/2555',
        status='in_force',
        effective_date=date(2024, 10, 17),
        source_url='https://eur-lex.europa.eu/eli/dir/2022/2555',
        description='NIS2 directive',
    )
    db_session.session.add(reg)
    db_session.session.commit()

    loaded = Regulation.query.filter_by(slug='nis2').one()
    assert loaded.short_code == 'NIS2'
    assert loaded.status == 'in_force'
    assert loaded.effective_date == date(2024, 10, 17)
    assert loaded.source_url.startswith('https://')


def test_audit_session_links_to_regulation(db_session):
    """AuditSession.regulation_id replaces the old standard_id link."""
    user_id = _make_user(db_session)
    reg = Regulation(name='NIS2', short_code='NIS2', slug='nis2', status='in_force')
    db_session.session.add(reg)
    db_session.session.flush()

    sess = AuditSession(user_id=user_id, title='Audit X', regulation_id=reg.id)
    db_session.session.add(sess)
    db_session.session.commit()

    loaded = AuditSession.query.filter_by(title='Audit X').one()
    assert loaded.regulation_id == reg.id
    assert loaded.regulation.short_code == 'NIS2'


def test_regulation_check_maps_regulation_to_check(db_session, seed_data):
    """RegulationCheck links a regulation to an existing technical check."""
    check = seed_data['checks'][0]
    reg = Regulation(name='NIS2', short_code='NIS2', slug='nis2', status='in_force')
    db_session.session.add(reg)
    db_session.session.flush()

    rc = RegulationCheck(
        regulation_id=reg.id,
        check_id=check.id,
        article='Art.21(2)(a)',
        requirement='IS security policies',
    )
    db_session.session.add(rc)
    db_session.session.commit()

    loaded = RegulationCheck.query.one()
    assert loaded.check.id == check.id
    assert loaded.article == 'Art.21(2)(a)'


def _make_user(db_session):
    from app.models import User
    u = User(username='reguser', display_name='Reg User', role='auditor', is_approved=True)
    u.set_password('password123')
    db_session.session.add(u)
    db_session.session.flush()
    return u.id
