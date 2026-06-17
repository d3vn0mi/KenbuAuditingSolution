"""End-to-end smoke: every compliance page renders 200 with real data.

Catches template / url_for / relationship errors that per-route unit tests miss.
"""
import io
import json

from app.extensions import db
from app.models import (
    Regulation, Obligation, Control, ControlReference, EvidenceRequirement,
    ReadinessAssessment, ControlStatus, Evidence, EvidenceVersion, Finding,
    Incident, Supplier,
)
from app.utils import sbom as sbom_util
from datetime import datetime, timezone, date


def _seed_everything(db_session, check):
    reg = Regulation(name='NIS2 Directive', short_code='NIS2', slug='nis2',
                     version='2022/2555', status='in_force')
    db.session.add(reg)
    db.session.flush()
    parent = Obligation(regulation_id=reg.id, ref='Art.21', title='Measures')
    db.session.add(parent)
    db.session.flush()
    ob = Obligation(regulation_id=reg.id, parent_id=parent.id, ref='Art.21(2)(d)',
                    title='Supply chain')
    db.session.add(ob)
    db.session.flush()

    control = Control(code='SC-01', title='Supply-chain RM', domain='SupplyChain')
    control.obligations.append(ob)
    control.checks.append(check)
    control.references.append(ControlReference(framework='ISO27001', ref_code='A.5.19'))
    control.evidence_requirements.append(
        EvidenceRequirement(title='Supplier register', type='document', cadence_days=365))
    db.session.add(control)
    db.session.flush()

    a = ReadinessAssessment(title='Q2 NIS2', regulation_id=reg.id, status='active')
    db.session.add(a)
    db.session.flush()
    db.session.add(ControlStatus(assessment_id=a.id, control_id=control.id,
                                 status='implemented'))

    ev = Evidence(title='Register doc', valid_until=date(2027, 1, 1))
    ev.controls.append(control)
    db.session.add(ev)
    db.session.flush()
    db.session.add(EvidenceVersion(evidence_id=ev.id, version=1, content_hash='a' * 64,
                                   storage_name='x', original_filename='r.pdf', size=5))

    finding = Finding(title='Bypass', severity='high', source='tlpt', status='open')
    finding.controls.append(control)
    db.session.add(finding)

    incident = Incident(title='Outage', severity='high',
                        detected_at=datetime(2026, 6, 1, tzinfo=timezone.utc))
    db.session.add(incident)

    supplier = Supplier(name='Acme', criticality='high', status='under_review')
    supplier.controls.append(control)
    db.session.add(supplier)
    db.session.flush()
    sbom = sbom_util.ingest_sbom(
        supplier, 'bom.json',
        json.dumps({'bomFormat': 'CycloneDX', 'components': [{'name': 'openssl', 'version': '3'}]}))
    db.session.commit()
    return {'reg': reg, 'control': control, 'a': a, 'ev': ev, 'finding': finding,
            'incident': incident, 'supplier': supplier, 'sbom': sbom}


def test_all_pages_render_for_admin(admin_client, db_session, seed_data, tmp_path):
    # evidence/export need a writable dir
    from flask import current_app
    current_app.config['EVIDENCE_DIR'] = str(tmp_path)
    d = _seed_everything(db_session, seed_data['checks'][0])

    pages = [
        '/',
        '/benchmarks/', '/regulations/', f"/regulations/{d['reg'].slug}",
        f"/regulations/controls/{d['control'].code}",
        '/readiness/', f"/readiness/{d['a'].id}", '/readiness/new',
        f"/readiness/{d['a'].id}/export.xlsx", f"/readiness/{d['a'].id}/export.pdf",
        '/evidence/', f"/evidence/{d['ev'].id}", '/evidence/new',
        '/findings/', f"/findings/{d['finding'].id}", '/findings/new', '/findings/import',
        '/incidents/', f"/incidents/{d['incident'].id}", '/incidents/new',
        f"/incidents/{d['incident'].id}/report/notification",
        '/suppliers/', f"/suppliers/{d['supplier'].id}", '/suppliers/new',
        f"/suppliers/{d['supplier'].id}/sbom/{d['sbom'].id}",
        '/admin/users', '/admin/activity',
    ]
    failures = []
    for url in pages:
        resp = admin_client.get(url)
        if resp.status_code != 200:
            failures.append((url, resp.status_code))
    assert not failures, f'pages did not render: {failures}'
