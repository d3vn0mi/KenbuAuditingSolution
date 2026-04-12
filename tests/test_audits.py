import pytest
from app.models.audit import AuditSession, AuditAsset, AuditAssetBenchmark, AuditResult


def _create_audit(auth_client, title='Test Audit'):
    """Helper: create an audit session and return its ID from the redirect."""
    resp = auth_client.post('/audits/new', data={'title': title})
    assert resp.status_code == 302
    return int(resp.headers['Location'].rstrip('/').split('/')[-1])


def _add_asset(auth_client, session_id, name='Server1', asset_type='linux'):
    """Helper: add an asset and return its ID."""
    resp = auth_client.post(f'/audits/{session_id}/assets/new', data={
        'name': name,
        'asset_type': asset_type,
    })
    assert resp.status_code == 302
    parts = resp.headers['Location'].rstrip('/').split('/')
    return int(parts[-2])  # asset_id


def _assign_benchmarks(auth_client, session_id, asset_id, benchmark_id):
    """Helper: assign a benchmark to an asset."""
    resp = auth_client.post(
        f'/audits/{session_id}/assets/{asset_id}/benchmarks',
        data={'benchmark_ids': benchmark_id},
    )
    assert resp.status_code == 302


def _start_audit(auth_client, session_id):
    """Helper: start an audit session."""
    resp = auth_client.post(f'/audits/{session_id}/start')
    assert resp.status_code == 302


class TestAuditList:
    def test_list_audits_empty(self, auth_client):
        resp = auth_client.get('/audits/')
        assert resp.status_code == 200


class TestAuditCreate:
    def test_create_audit(self, auth_client):
        sid = _create_audit(auth_client)
        session = AuditSession.query.get(sid)
        assert session is not None
        assert session.title == 'Test Audit'
        assert session.status == 'draft'

    def test_create_without_title(self, auth_client):
        resp = auth_client.post('/audits/new', data={'title': ''}, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Title is required' in resp.data


class TestAuditDetail:
    def test_view_session_detail(self, auth_client):
        sid = _create_audit(auth_client)
        resp = auth_client.get(f'/audits/{sid}')
        assert resp.status_code == 200
        assert b'Test Audit' in resp.data

    def test_edit_draft_session(self, auth_client):
        sid = _create_audit(auth_client)
        resp = auth_client.post(f'/audits/{sid}/edit', data={
            'title': 'Updated Title',
            'description': 'New description',
        }, follow_redirects=True)
        assert resp.status_code == 200
        session = AuditSession.query.get(sid)
        assert session.title == 'Updated Title'

    def test_edit_non_draft_session(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        resp = auth_client.post(f'/audits/{sid}/edit', data={
            'title': 'Should Not Change',
        }, follow_redirects=True)
        assert b'not in draft status' in resp.data


class TestAuditAssets:
    def test_add_asset(self, auth_client):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        asset = AuditAsset.query.get(aid)
        assert asset is not None
        assert asset.name == 'Server1'

    def test_assign_benchmarks(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        mappings = AuditAssetBenchmark.query.filter_by(asset_id=aid).all()
        assert len(mappings) == 1


class TestAuditLifecycle:
    def test_start_session(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        session = AuditSession.query.get(sid)
        assert session.status == 'in_progress'
        assert session.started_at is not None
        results = AuditResult.query.filter_by(asset_id=aid).all()
        assert len(results) == 3

    def test_start_without_assets(self, auth_client):
        sid = _create_audit(auth_client)
        resp = auth_client.post(f'/audits/{sid}/start', follow_redirects=True)
        assert b'at least one asset' in resp.data

    def test_start_with_unassigned_benchmarks(self, auth_client):
        sid = _create_audit(auth_client)
        _add_asset(auth_client, sid)
        resp = auth_client.post(f'/audits/{sid}/start', follow_redirects=True)
        assert b'no benchmarks assigned' in resp.data

    def test_update_single_result(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        check_id = seed_data['checks'][0].id
        resp = auth_client.post(
            f'/audits/{sid}/assets/{aid}/check/{check_id}',
            data={'status': 'pass', 'finding': 'Looks good'},
        )
        assert resp.status_code == 302
        result = AuditResult.query.filter_by(asset_id=aid, check_id=check_id).first()
        assert result.status == 'pass'
        assert result.finding == 'Looks good'
        assert result.checked_at is not None

    def test_bulk_update_results(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        check_ids = [c.id for c in seed_data['checks']]
        resp = auth_client.post(
            f'/audits/{sid}/assets/{aid}/bulk-update',
            data={'bulk_status': 'pass', 'check_ids': check_ids},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        for cid in check_ids:
            result = AuditResult.query.filter_by(asset_id=aid, check_id=cid).first()
            assert result.status == 'pass'

    def test_complete_session(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        resp = auth_client.post(f'/audits/{sid}/complete')
        assert resp.status_code == 302
        session = AuditSession.query.get(sid)
        assert session.status == 'completed'
        assert session.completed_at is not None


class TestAuditDelete:
    def test_delete_draft_session(self, auth_client):
        sid = _create_audit(auth_client)
        resp = auth_client.post(f'/audits/{sid}/delete', follow_redirects=True)
        assert resp.status_code == 200
        assert AuditSession.query.get(sid) is None

    def test_delete_non_draft_session(self, auth_client, seed_data):
        sid = _create_audit(auth_client)
        aid = _add_asset(auth_client, sid)
        _assign_benchmarks(auth_client, sid, aid, seed_data['benchmark'].id)
        _start_audit(auth_client, sid)

        resp = auth_client.post(f'/audits/{sid}/delete', follow_redirects=True)
        assert b'not in draft status' in resp.data
        assert AuditSession.query.get(sid) is not None


class TestAuditAccessControl:
    def test_access_other_users_session(self, auth_client, db_session):
        """Verify that viewing another user's audit session returns 403."""
        from tests.conftest import _create_user

        # Create an audit owned by a different user
        other_user = _create_user(db_session, 'other_user', 'password123', role='auditor')
        other_session = AuditSession(
            user_id=other_user.id,
            title='Private Audit',
        )
        db_session.session.add(other_session)
        db_session.session.commit()

        # The auth_client is logged in as 'testauditor', not 'other_user'
        resp = auth_client.get(f'/audits/{other_session.id}')
        assert resp.status_code == 403
