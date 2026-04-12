import pytest
from app.models.audit import AuditSession, AuditAsset, AuditAssetBenchmark, AuditResult
from app.models.hardening import HardeningTask, HardeningAsset, HardeningAssetBenchmark, HardeningCheckResult

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class TestBenchmarkExport:
    def test_export_benchmark(self, auth_client, seed_data):
        bid = seed_data['benchmark'].id
        resp = auth_client.get(f'/export/benchmark/{bid}')
        assert resp.status_code == 200
        assert resp.content_type == XLSX_MIME
        assert len(resp.data) > 0


class TestAuditExport:
    def test_export_audit(self, auth_client, seed_data, auditor_user):
        from app.extensions import db
        session = AuditSession(
            user_id=auditor_user.id,
            title='Export Test Audit',
            status='in_progress',
        )
        db.session.add(session)
        db.session.flush()

        asset = AuditAsset(
            session_id=session.id,
            name='TestServer',
            asset_type='linux',
        )
        db.session.add(asset)
        db.session.flush()

        for check in seed_data['checks']:
            result = AuditResult(asset_id=asset.id, check_id=check.id, status='pass')
            db.session.add(result)
        db.session.commit()

        resp = auth_client.get(f'/export/audit/{session.id}')
        assert resp.status_code == 200
        assert resp.content_type == XLSX_MIME
        assert len(resp.data) > 0


class TestHardeningExport:
    def test_export_hardening_excel(self, auth_client, seed_data, auditor_user):
        from app.extensions import db

        task = HardeningTask(
            user_id=auditor_user.id,
            title='Export Test Hardening',
            status='in_progress',
        )
        db.session.add(task)
        db.session.flush()

        asset = HardeningAsset(
            task_id=task.id,
            name='TestServer',
            asset_type='linux',
        )
        db.session.add(asset)
        db.session.flush()

        for check in seed_data['checks']:
            result = HardeningCheckResult(asset_id=asset.id, check_id=check.id, status='done')
            db.session.add(result)
        db.session.commit()

        resp = auth_client.get(f'/export/hardening/{task.id}/excel')
        assert resp.status_code == 200
        assert resp.content_type == XLSX_MIME
        assert len(resp.data) > 0
