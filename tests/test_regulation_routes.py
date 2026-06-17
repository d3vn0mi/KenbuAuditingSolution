"""Tests for the regulatory browse UI (Phase 1)."""
from app.models import (
    Regulation, Obligation, Control, ControlReference, EvidenceRequirement,
)


def _seed_reg_layer(db_session, seed_data):
    check = seed_data['checks'][0]  # check_number '1.1'
    reg = Regulation(name='NIS2 Directive', short_code='NIS2', slug='nis2',
                     status='in_force', version='2022/2555')
    db_session.session.add(reg)
    db_session.session.flush()
    parent = Obligation(regulation_id=reg.id, ref='Art.21', title='Risk-management measures')
    db_session.session.add(parent)
    db_session.session.flush()
    ob = Obligation(regulation_id=reg.id, parent_id=parent.id,
                    ref='Art.21(2)(d)', title='Supply chain security')
    db_session.session.add(ob)
    db_session.session.flush()
    control = Control(code='SC-01', title='Supply-chain risk management', domain='SupplyChain')
    control.obligations.append(ob)
    control.checks.append(check)
    control.references.append(ControlReference(framework='ISO27001', ref_code='A.5.19',
                                               title='Supplier relationships'))
    control.evidence_requirements.append(EvidenceRequirement(
        title='Approved supplier register', type='document', cadence_days=365))
    db_session.session.add(control)
    db_session.session.commit()
    return reg, ob, control


def test_list_regulations_requires_login(client):
    resp = client.get('/regulations/')
    assert resp.status_code in (301, 302)
    assert '/auth/login' in resp.headers.get('Location', '')


def test_list_regulations_shows_regulations(auth_client, db_session, seed_data):
    _seed_reg_layer(db_session, seed_data)
    resp = auth_client.get('/regulations/')
    assert resp.status_code == 200
    assert b'NIS2' in resp.data


def test_regulation_detail_shows_obligations_and_controls(auth_client, db_session, seed_data):
    _seed_reg_layer(db_session, seed_data)
    resp = auth_client.get('/regulations/nis2')
    assert resp.status_code == 200
    assert b'Art.21' in resp.data           # parent obligation (recursive macro)
    assert b'Art.21(2)(d)' in resp.data     # nested child obligation
    assert b'SC-01' in resp.data


def test_control_detail_shows_checks_and_cross_mapping(auth_client, db_session, seed_data):
    _seed_reg_layer(db_session, seed_data)
    resp = auth_client.get('/regulations/controls/SC-01')
    assert resp.status_code == 200
    assert b'SC-01' in resp.data
    assert b'1.1' in resp.data            # linked technical check number
    assert b'Art.21(2)(d)' in resp.data   # cross-mapping to obligation
    assert b'ISO27001' in resp.data       # standard reference
    assert b'supplier register' in resp.data.lower()  # evidence requirement
