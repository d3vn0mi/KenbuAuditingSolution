"""Tests for supplier register + SBOM upload routes (Phase 4 m9)."""
import io
import json

from app.models import Supplier, SBOM
from tests.conftest import _create_user, _login


def test_suppliers_requires_compliance(app, client, db_session):
    _create_user(db_session, 'eng', 'password123', role='security_engineer')
    _login(client, 'eng', 'password123')
    assert client.get('/suppliers/').status_code == 403


def test_new_supplier(auth_client, db_session):
    resp = auth_client.post('/suppliers/new', data={
        'name': 'Orbital Components Ltd', 'criticality': 'high', 'country': 'DE',
    }, follow_redirects=True)
    assert resp.status_code == 200
    s = Supplier.query.filter_by(name='Orbital Components Ltd').one()
    assert s.criticality == 'high'
    assert s.status == 'under_review'


def test_upload_sbom_parses_components(auth_client, db_session):
    s = Supplier(name='Acme', criticality='high', status='under_review')
    db_session.session.add(s)
    db_session.session.commit()

    bom = json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.5",
                      "components": [{"name": "openssl", "version": "3.0.0"},
                                     {"name": "zlib", "version": "1.2.13"}]})
    resp = auth_client.post(f'/suppliers/{s.id}/sbom', data={
        'file': (io.BytesIO(bom.encode()), 'bom.json'),
    }, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200
    sbom = SBOM.query.filter_by(supplier_id=s.id).one()
    assert sbom.format == 'cyclonedx'
    assert sbom.component_count == 2
    assert b'openssl' in resp.data  # component table rendered
