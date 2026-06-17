"""Tests for the Control hub: obligations, controls, mappings (Phase 1 m2)."""
from app.models import (
    Regulation, Obligation, Control, EvidenceRequirement, ControlReference, Check,
)


def _make_regulation(db_session, slug='nis2', short='NIS2'):
    reg = Regulation(name=short, short_code=short, slug=slug, status='in_force')
    db_session.session.add(reg)
    db_session.session.flush()
    return reg


def test_obligation_hierarchy(db_session):
    """Obligations belong to a regulation and nest via parent/children."""
    reg = _make_regulation(db_session)
    parent = Obligation(regulation_id=reg.id, ref='Art.21', title='Risk-management measures')
    db_session.session.add(parent)
    db_session.session.flush()
    child = Obligation(regulation_id=reg.id, parent_id=parent.id,
                       ref='Art.21(2)(d)', title='Supply chain security')
    db_session.session.add(child)
    db_session.session.commit()

    assert child.parent.ref == 'Art.21'
    assert parent.children.count() == 1
    assert child.regulation.short_code == 'NIS2'


def test_control_maps_to_obligations_across_regulations(db_session):
    """A single control can satisfy obligations from different regulations."""
    nis2 = _make_regulation(db_session, slug='nis2', short='NIS2')
    eusa = _make_regulation(db_session, slug='eu-space-act', short='EUSA')
    ob_nis2 = Obligation(regulation_id=nis2.id, ref='Art.21(2)(d)', title='Supply chain')
    ob_eusa = Obligation(regulation_id=eusa.id, ref='Art.80', title='Supply-chain RM')
    db_session.session.add_all([ob_nis2, ob_eusa])
    db_session.session.flush()

    control = Control(code='SC-01', title='Supply-chain risk management',
                      domain='SupplyChain')
    control.obligations.extend([ob_nis2, ob_eusa])
    db_session.session.add(control)
    db_session.session.commit()

    loaded = Control.query.filter_by(code='SC-01').one()
    refs = {o.ref for o in loaded.obligations}
    assert refs == {'Art.21(2)(d)', 'Art.80'}
    # And the reverse: the obligation knows its controls
    assert ob_nis2.controls[0].code == 'SC-01'


def test_control_links_to_technical_check(db_session, seed_data):
    """A control is evidenced by existing CIS checks; Check.controls is the reverse."""
    check = seed_data['checks'][0]
    control = Control(code='SC-01', title='Supply-chain RM', domain='SupplyChain')
    control.checks.append(check)
    db_session.session.add(control)
    db_session.session.commit()

    loaded = Control.query.filter_by(code='SC-01').one()
    assert loaded.checks[0].id == check.id
    assert check.controls[0].code == 'SC-01'


def test_control_has_evidence_requirements_and_references(db_session):
    """Controls carry evidence requirements and cross-framework references."""
    control = Control(code='SC-01', title='Supply-chain RM', domain='SupplyChain')
    control.evidence_requirements.append(
        EvidenceRequirement(title='Approved supplier register', type='document',
                            cadence_days=365)
    )
    control.references.append(
        ControlReference(framework='ISO27001', ref_code='A.5.19',
                         title='Supplier relationships')
    )
    db_session.session.add(control)
    db_session.session.commit()

    loaded = Control.query.filter_by(code='SC-01').one()
    assert loaded.evidence_requirements[0].cadence_days == 365
    assert loaded.references[0].framework == 'ISO27001'
