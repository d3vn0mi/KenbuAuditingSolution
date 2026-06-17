"""Tests for the evidence repository routes (Phase 2 m6)."""
import io
from datetime import date, timedelta

from app.models import Evidence, Control
from tests.conftest import _create_user, _login


def test_evidence_requires_compliance(app, client, db_session):
    _create_user(db_session, 'eng', 'password123', role='security_engineer')
    _login(client, 'eng', 'password123')
    assert client.get('/evidence/').status_code == 403


def test_upload_then_download_roundtrip(app, auth_client, db_session, tmp_path):
    app.config['EVIDENCE_DIR'] = str(tmp_path)
    control = Control(code='SC-01', title='Supply-chain RM', domain='SupplyChain')
    db_session.session.add(control)
    db_session.session.commit()

    body = b'%PDF-1.4 fake evidence body'
    resp = auth_client.post('/evidence/new', data={
        'title': 'Supplier register',
        'evidence_type': 'document',
        'control_ids': str(control.id),
        'file': (io.BytesIO(body), 'register.pdf'),
    }, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200

    ev = Evidence.query.filter_by(title='Supplier register').one()
    version = ev.current_version
    assert version is not None
    assert version.original_filename == 'register.pdf'
    assert version.content_hash  # integrity hash recorded
    assert control in ev.controls

    # Download returns the original plaintext (decrypted + integrity-checked)
    dl = auth_client.get(f'/evidence/{ev.id}/version/{version.id}/download')
    assert dl.status_code == 200
    assert dl.data == body


def test_second_version_increments(app, auth_client, db_session, tmp_path):
    app.config['EVIDENCE_DIR'] = str(tmp_path)
    auth_client.post('/evidence/new', data={
        'title': 'Policy', 'file': (io.BytesIO(b'v1'), 'p.txt'),
    }, content_type='multipart/form-data', follow_redirects=True)
    ev = Evidence.query.filter_by(title='Policy').one()

    auth_client.post(f'/evidence/{ev.id}/version', data={
        'file': (io.BytesIO(b'v2 content'), 'p.txt'),
    }, content_type='multipart/form-data', follow_redirects=True)

    versions = ev.versions.all()
    assert [v.version for v in versions] == [2, 1]  # ordered desc
    assert ev.current_version.version == 2


def test_tampered_download_returns_409(app, auth_client, db_session, tmp_path):
    app.config['EVIDENCE_DIR'] = str(tmp_path)
    auth_client.post('/evidence/new', data={
        'title': 'Doc', 'file': (io.BytesIO(b'real'), 'd.txt'),
    }, content_type='multipart/form-data', follow_redirects=True)
    ev = Evidence.query.filter_by(title='Doc').one()
    v = ev.current_version
    # corrupt the encrypted file on disk
    from app.utils import evidence_store
    with open(evidence_store.storage_path(v.storage_name), 'wb') as f:
        f.write(b'tampered')
    resp = auth_client.get(f'/evidence/{ev.id}/version/{v.id}/download')
    assert resp.status_code == 409


def test_expired_evidence_flagged(auth_client, db_session):
    ev = Evidence(title='Old cert', valid_until=date.today() - timedelta(days=1))
    db_session.session.add(ev)
    db_session.session.commit()
    assert ev.is_expired is True
    resp = auth_client.get('/evidence/')
    assert b'expired' in resp.data
