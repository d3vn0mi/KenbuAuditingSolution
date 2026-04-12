import pytest
from app.models.hardening import HardeningTask, HardeningAsset, HardeningAssetBenchmark, HardeningCheckResult


def _create_task(auth_client, title='Test Hardening'):
    resp = auth_client.post('/hardening/new', data={'title': title})
    assert resp.status_code == 302
    return int(resp.headers['Location'].rstrip('/').split('/')[-1])


def _add_asset(auth_client, task_id, name='Server1', asset_type='linux'):
    resp = auth_client.post(f'/hardening/{task_id}/assets/new', data={
        'name': name,
        'asset_type': asset_type,
    })
    assert resp.status_code == 302
    parts = resp.headers['Location'].rstrip('/').split('/')
    return int(parts[-2])


def _assign_benchmarks(auth_client, task_id, asset_id, benchmark_id):
    resp = auth_client.post(
        f'/hardening/{task_id}/assets/{asset_id}/benchmarks',
        data={'benchmark_ids': benchmark_id},
    )
    assert resp.status_code == 302


def _start_task(auth_client, task_id):
    resp = auth_client.post(f'/hardening/{task_id}/start')
    assert resp.status_code == 302


class TestHardeningList:
    def test_list_tasks_empty(self, auth_client):
        resp = auth_client.get('/hardening/')
        assert resp.status_code == 200


class TestHardeningCreate:
    def test_create_task(self, auth_client):
        tid = _create_task(auth_client)
        task = HardeningTask.query.get(tid)
        assert task is not None
        assert task.title == 'Test Hardening'
        assert task.status == 'draft'

    def test_create_without_title(self, auth_client):
        resp = auth_client.post('/hardening/new', data={'title': ''}, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Title is required' in resp.data


class TestHardeningAssets:
    def test_add_asset(self, auth_client):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        asset = HardeningAsset.query.get(aid)
        assert asset is not None
        assert asset.name == 'Server1'

    def test_assign_benchmarks(self, auth_client, seed_data):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        _assign_benchmarks(auth_client, tid, aid, seed_data['benchmark'].id)
        mappings = HardeningAssetBenchmark.query.filter_by(asset_id=aid).all()
        assert len(mappings) == 1


class TestHardeningLifecycle:
    def test_start_task(self, auth_client, seed_data):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        _assign_benchmarks(auth_client, tid, aid, seed_data['benchmark'].id)
        _start_task(auth_client, tid)

        task = HardeningTask.query.get(tid)
        assert task.status == 'in_progress'
        assert task.started_at is not None
        results = HardeningCheckResult.query.filter_by(asset_id=aid).all()
        assert len(results) == 3

    def test_start_without_assets(self, auth_client):
        tid = _create_task(auth_client)
        resp = auth_client.post(f'/hardening/{tid}/start', follow_redirects=True)
        assert b'at least one asset' in resp.data

    def test_update_single_check(self, auth_client, seed_data):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        _assign_benchmarks(auth_client, tid, aid, seed_data['benchmark'].id)
        _start_task(auth_client, tid)

        check_id = seed_data['checks'][0].id
        resp = auth_client.post(
            f'/hardening/{tid}/assets/{aid}/check/{check_id}',
            data={'status': 'done', 'notes': 'Applied fix'},
        )
        assert resp.status_code == 302
        result = HardeningCheckResult.query.filter_by(asset_id=aid, check_id=check_id).first()
        assert result.status == 'done'
        assert result.notes == 'Applied fix'

    def test_bulk_update_checks(self, auth_client, seed_data):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        _assign_benchmarks(auth_client, tid, aid, seed_data['benchmark'].id)
        _start_task(auth_client, tid)

        check_ids = [c.id for c in seed_data['checks']]
        resp = auth_client.post(
            f'/hardening/{tid}/assets/{aid}/bulk-update',
            data={'bulk_status': 'done', 'check_ids': check_ids},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        for cid in check_ids:
            result = HardeningCheckResult.query.filter_by(asset_id=aid, check_id=cid).first()
            assert result.status == 'done'

    def test_complete_task(self, auth_client, seed_data):
        tid = _create_task(auth_client)
        aid = _add_asset(auth_client, tid)
        _assign_benchmarks(auth_client, tid, aid, seed_data['benchmark'].id)
        _start_task(auth_client, tid)

        resp = auth_client.post(f'/hardening/{tid}/complete')
        assert resp.status_code == 302
        task = HardeningTask.query.get(tid)
        assert task.status == 'completed'


class TestHardeningDelete:
    def test_delete_draft_task(self, auth_client):
        tid = _create_task(auth_client)
        resp = auth_client.post(f'/hardening/{tid}/delete', follow_redirects=True)
        assert resp.status_code == 200
        assert HardeningTask.query.get(tid) is None


class TestHardeningAccessControl:
    def test_access_other_users_task(self, app, db_session, seed_data):
        from tests.conftest import _create_user, _login

        _create_user(db_session, 'harden_a', 'password123', role='auditor')
        _create_user(db_session, 'harden_b', 'password123', role='auditor')

        with app.test_client() as client:
            # Log in as user A and create a task
            _login(client, 'harden_a', 'password123')
            tid = _create_task(client)

            # Log out, then log in as user B
            client.post('/auth/logout')
            _login(client, 'harden_b', 'password123')

            # User B should not be able to access user A's task
            resp = client.get(f'/hardening/{tid}')
            assert resp.status_code == 403
