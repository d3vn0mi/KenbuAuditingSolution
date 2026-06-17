"""Tests for findings and finding->control readiness impact (Phase 2 m7)."""
from app.models import (
    Control, ReadinessAssessment, ControlStatus, Finding,
)
from app.utils import readiness as scoring
from app.utils import findings as findings_service


def _assessment_with_implemented_control(db_session):
    control = Control(code='IAM-01', title='Access control', domain='IAM')
    db_session.session.add(control)
    db_session.session.flush()
    a = ReadinessAssessment(title='A', status='active')
    db_session.session.add(a)
    db_session.session.flush()
    db_session.session.add(ControlStatus(assessment_id=a.id, control_id=control.id,
                                         status='implemented'))
    db_session.session.commit()
    return a, control


def test_open_high_finding_caps_readiness(db_session):
    a, control = _assessment_with_implemented_control(db_session)
    assert abs(scoring.assessment_score(a) - 1.0) < 1e-9  # baseline: fully implemented

    finding = Finding(title='Auth bypass', severity='high', source='tlpt', status='open')
    finding.controls.append(control)
    db_session.session.add(finding)
    db_session.session.commit()

    sevs = scoring.open_finding_severities(a)
    # implemented control capped to 'partial' (0.5) by the open high finding
    assert abs(scoring.assessment_score(a, finding_severities=sevs) - 0.5) < 1e-9


def test_remediated_finding_does_not_cap(db_session):
    a, control = _assessment_with_implemented_control(db_session)
    finding = Finding(title='Old issue', severity='critical', source='pentest',
                      status='remediated')
    finding.controls.append(control)
    db_session.session.add(finding)
    db_session.session.commit()

    sevs = scoring.open_finding_severities(a)
    assert abs(scoring.assessment_score(a, finding_severities=sevs) - 1.0) < 1e-9


def test_import_findings_creates_and_links(db_session):
    control = Control(code='SC-01', title='Supply chain', domain='SupplyChain')
    db_session.session.add(control)
    db_session.session.commit()

    rows = [
        {'title': 'Vuln A', 'severity': 'high', 'source': 'tlpt',
         'description': 'desc', 'controls': ['SC-01']},
        {'title': 'Vuln B', 'severity': 'low', 'source': 'scan'},
    ]
    created = findings_service.import_findings(rows)
    assert len(created) == 2
    a = Finding.query.filter_by(title='Vuln A').one()
    assert a.severity == 'high'
    assert a.controls[0].code == 'SC-01'
