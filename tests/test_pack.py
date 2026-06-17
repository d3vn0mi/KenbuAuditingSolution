"""Tests for the evidence/readiness pack export (Phase 3)."""
from datetime import datetime, timezone, date

from app.models import (
    Regulation, Obligation, Control, ReadinessAssessment, ControlStatus,
    Evidence, EvidenceVersion,
)
from app.utils import pack
from app.utils.excel_export import export_readiness_to_excel

GEN_AT = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)


def _full_assessment(db_session):
    reg = Regulation(name='NIS2 Directive', short_code='NIS2', slug='nis2',
                     version='2022/2555', status='in_force')
    db_session.session.add(reg)
    db_session.session.flush()
    ob = Obligation(regulation_id=reg.id, ref='Art.21(2)(d)', title='Supply chain')
    db_session.session.add(ob)
    db_session.session.flush()
    control = Control(code='SC-01', title='Supply-chain RM', domain='SupplyChain')
    control.obligations.append(ob)
    db_session.session.add(control)
    db_session.session.flush()

    ev = Evidence(title='Supplier register', valid_until=date(2027, 1, 1))
    ev.controls.append(control)
    db_session.session.add(ev)
    db_session.session.flush()
    db_session.session.add(EvidenceVersion(
        evidence_id=ev.id, version=1, content_hash='a' * 64,
        storage_name='deadbeef', original_filename='reg.pdf', size=10))

    a = ReadinessAssessment(title='Q2 NIS2', regulation_id=reg.id, status='active')
    db_session.session.add(a)
    db_session.session.flush()
    db_session.session.add(ControlStatus(assessment_id=a.id, control_id=control.id,
                                         status='implemented'))
    db_session.session.commit()
    return a, control, ev


def test_build_context_has_core_sections(db_session):
    a, control, ev = _full_assessment(db_session)
    ctx = pack.build_context(a, generated_at=GEN_AT)
    assert ctx['assessment'].id == a.id
    assert ctx['regulation'].short_code == 'NIS2'
    assert abs(ctx['overall'] - 1.0) < 1e-9
    # evidence index maps the control to its evidence + integrity hash
    index = ctx['evidence_index']
    assert any(row['control'].code == 'SC-01' and ev in row['evidence'] for row in index)
    assert ctx['generated_at'] == GEN_AT


def test_export_excel_is_valid_workbook(db_session):
    a, _, _ = _full_assessment(db_session)
    out = export_readiness_to_excel(a, generated_at=GEN_AT)
    data = out.getvalue()
    assert data[:2] == b'PK'        # xlsx is a zip
    assert len(data) > 2000


def test_render_pdf_is_valid_pdf(db_session):
    a, _, _ = _full_assessment(db_session)
    data = pack.render_pdf(a, generated_at=GEN_AT)
    assert data[:5] == b'%PDF-'
    assert len(data) > 2000
