from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from ..extensions import db
from ..models import Benchmark, BenchmarkSection, Check
from ..models.audit import AuditSession, AuditAsset, AuditAssetBenchmark, AuditResult
from ..models.standard import Standard, StandardCheck
from ..utils.auth import auditor_required

audits_bp = Blueprint('audits', __name__, url_prefix='/audits')


@audits_bp.route('/')
@auditor_required
def list_audits():
    sessions = AuditSession.query.filter_by(
        user_id=current_user.id
    ).order_by(AuditSession.created_at.desc()).all()
    return render_template('audits/list.html', sessions=sessions)


@audits_bp.route('/new', methods=['GET', 'POST'])
@auditor_required
def new_audit():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        standard_id = request.form.get('standard_id', type=int)
        notes = request.form.get('notes', '').strip()

        if not title:
            flash('Title is required.', 'error')
            standards = Standard.query.order_by(Standard.name).all()
            return render_template('audits/new.html', standards=standards)

        session = AuditSession(
            user_id=current_user.id,
            title=title,
            description=description or None,
            standard_id=standard_id if standard_id else None,
            notes=notes or None,
        )
        db.session.add(session)
        db.session.commit()
        flash('Audit session created.', 'success')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    standards = Standard.query.order_by(Standard.name).all()
    return render_template('audits/new.html', standards=standards)


@audits_bp.route('/<int:session_id>')
@auditor_required
def session_detail(session_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)

    assets = session.assets.all()
    standards = []
    if session.status == 'draft':
        from ..models.standard import Standard
        standards = Standard.query.order_by(Standard.name).all()
    return render_template('audits/detail.html', session=session, assets=assets, standards=standards)


@audits_bp.route('/<int:session_id>/edit', methods=['POST'])
@auditor_required
def edit_session(session_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)
    if session.status != 'draft':
        flash('Cannot edit a session that is not in draft status.', 'error')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    standard_id = request.form.get('standard_id', type=int)

    if not title:
        flash('Title is required.', 'error')
    else:
        session.title = title
        session.description = description or None
        session.standard_id = standard_id if standard_id else None
        db.session.commit()
        flash('Audit session updated.', 'success')

    return redirect(url_for('audits.session_detail', session_id=session.id))


@audits_bp.route('/<int:session_id>/delete', methods=['POST'])
@auditor_required
def delete_session(session_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)
    if session.status != 'draft':
        flash('Cannot delete a session that is not in draft status.', 'error')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    db.session.delete(session)
    db.session.commit()
    flash('Audit session deleted.', 'success')
    return redirect(url_for('audits.list_audits'))


@audits_bp.route('/<int:session_id>/assets/new', methods=['GET', 'POST'])
@auditor_required
def new_asset(session_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)
    if session.status not in ('draft', 'in_progress'):
        flash('Cannot add assets to a completed audit.', 'error')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        asset_type = request.form.get('asset_type', '').strip()
        ip_address = request.form.get('ip_address', '').strip()
        notes = request.form.get('notes', '').strip()

        if not name or not asset_type:
            flash('Name and type are required.', 'error')
            return render_template('audits/asset_new.html', session=session)

        asset = AuditAsset(
            session_id=session.id,
            name=name,
            asset_type=asset_type,
            ip_address=ip_address or None,
            notes=notes or None,
        )
        db.session.add(asset)
        db.session.commit()
        flash(f'Asset "{name}" added.', 'success')
        return redirect(url_for('audits.asset_benchmarks', session_id=session.id, asset_id=asset.id))

    return render_template('audits/asset_new.html', session=session)


@audits_bp.route('/<int:session_id>/assets/<int:asset_id>/delete', methods=['POST'])
@auditor_required
def delete_asset(session_id, asset_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)
    if session.status not in ('draft', 'in_progress'):
        flash('Cannot remove assets from a completed audit.', 'error')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    asset = AuditAsset.query.get_or_404(asset_id)
    if asset.session_id != session.id:
        abort(404)

    db.session.delete(asset)
    db.session.commit()
    flash(f'Asset "{asset.name}" removed.', 'success')
    return redirect(url_for('audits.session_detail', session_id=session.id))


@audits_bp.route('/<int:session_id>/assets/<int:asset_id>/benchmarks', methods=['GET', 'POST'])
@auditor_required
def asset_benchmarks(session_id, asset_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)
    if session.status not in ('draft', 'in_progress'):
        flash('Cannot modify benchmarks on a completed audit.', 'error')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    asset = AuditAsset.query.get_or_404(asset_id)
    if asset.session_id != session.id:
        abort(404)

    if request.method == 'POST':
        selected_ids = request.form.getlist('benchmark_ids', type=int)

        # Remove existing assignments
        AuditAssetBenchmark.query.filter_by(asset_id=asset.id).delete()

        # Add new assignments
        for bid in selected_ids:
            mapping = AuditAssetBenchmark(asset_id=asset.id, benchmark_id=bid)
            db.session.add(mapping)

        # If session is in_progress, regenerate results for this asset
        if session.status == 'in_progress':
            AuditResult.query.filter_by(asset_id=asset.id).delete()
            _generate_audit_results_for_asset(asset, session.standard_id)

        db.session.commit()
        flash(f'Benchmarks updated for "{asset.name}".', 'success')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    benchmarks = Benchmark.query.order_by(Benchmark.name).all()
    assigned_ids = {ab.benchmark_id for ab in asset.benchmarks}
    return render_template('audits/asset_benchmarks.html',
                           session=session, asset=asset,
                           benchmarks=benchmarks, assigned_ids=assigned_ids)


def _generate_audit_results_for_asset(asset, standard_id=None):
    """Generate AuditResult records for all checks in the asset's benchmarks,
    optionally filtered by a compliance standard."""
    benchmark_ids = [ab.benchmark_id for ab in asset.benchmarks]
    if not benchmark_ids:
        return 0

    checks_query = Check.query.join(BenchmarkSection).filter(
        BenchmarkSection.benchmark_id.in_(benchmark_ids)
    )

    # If a standard is selected, filter to only standard-mapped checks
    if standard_id:
        standard_check_ids = db.session.query(StandardCheck.check_id).filter(
            StandardCheck.standard_id == standard_id
        ).subquery()
        checks_query = checks_query.filter(Check.id.in_(standard_check_ids))

    checks = checks_query.all()
    for check in checks:
        result = AuditResult(asset_id=asset.id, check_id=check.id)
        db.session.add(result)
    return len(checks)


@audits_bp.route('/<int:session_id>/start', methods=['POST'])
@auditor_required
def start_session(session_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)
    if session.status != 'draft':
        flash('Audit is already started.', 'error')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    assets = session.assets.all()
    if not assets:
        flash('Add at least one asset before starting.', 'error')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    # Validate that each asset has at least one benchmark
    for asset in assets:
        if not asset.benchmarks:
            flash(f'Asset "{asset.name}" has no benchmarks assigned.', 'error')
            return redirect(url_for('audits.session_detail', session_id=session.id))

    # Generate audit results for all assets
    total_checks = 0
    for asset in assets:
        total_checks += _generate_audit_results_for_asset(asset, session.standard_id)

    session.status = 'in_progress'
    session.started_at = datetime.now(timezone.utc)
    db.session.commit()

    standard_note = ''
    if session.standard_id:
        standard_note = f' (filtered by {session.standard.name})'
    flash(f'Audit started with {total_checks} checks across {len(assets)} assets{standard_note}.', 'success')
    return redirect(url_for('audits.session_detail', session_id=session.id))


@audits_bp.route('/<int:session_id>/assets/<int:asset_id>')
@auditor_required
def asset_detail(session_id, asset_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)

    asset = AuditAsset.query.get_or_404(asset_id)
    if asset.session_id != session.id:
        abort(404)

    results = AuditResult.query.filter_by(
        asset_id=asset.id
    ).join(Check).order_by(Check.check_number).all()

    return render_template('audits/asset_detail.html',
                           session=session, asset=asset, results=results)


@audits_bp.route('/<int:session_id>/assets/<int:asset_id>/check/<int:check_id>', methods=['POST'])
@auditor_required
def update_result(session_id, asset_id, check_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)

    result = AuditResult.query.filter_by(
        asset_id=asset_id,
        check_id=check_id
    ).first_or_404()

    if result.asset.session_id != session.id:
        abort(404)

    status = request.form.get('status', 'not_checked')
    finding = request.form.get('finding', '').strip()

    if status in ('pass', 'fail', 'not_applicable', 'not_checked'):
        result.status = status
        result.finding = finding
        result.checked_at = datetime.now(timezone.utc) if status != 'not_checked' else None
        db.session.commit()

    if request.headers.get('HX-Request'):
        asset = result.asset
        all_results = AuditResult.query.filter_by(asset_id=asset.id).all()
        row_html = render_template('audits/_result_row.html',
                                   result=result, session=session, asset=asset)
        stats_html = render_template('audits/_asset_stats.html',
                                     asset=asset, results=all_results, oob=True)
        return row_html + stats_html

    return redirect(url_for('audits.asset_detail', session_id=session_id, asset_id=asset_id))


@audits_bp.route('/<int:session_id>/assets/<int:asset_id>/bulk-update', methods=['POST'])
@auditor_required
def bulk_update_results(session_id, asset_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)
    if session.status != 'in_progress':
        flash('Audit must be in progress to update checks.', 'error')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    asset = AuditAsset.query.get_or_404(asset_id)
    if asset.session_id != session.id:
        abort(404)

    status = request.form.get('bulk_status', '')
    check_ids = request.form.getlist('check_ids', type=int)

    if status not in ('pass', 'fail', 'not_applicable', 'not_checked'):
        flash('Invalid status.', 'error')
        return redirect(url_for('audits.asset_detail', session_id=session.id, asset_id=asset.id))

    if not check_ids:
        flash('No checks selected.', 'error')
        return redirect(url_for('audits.asset_detail', session_id=session.id, asset_id=asset.id))

    results = AuditResult.query.filter(
        AuditResult.asset_id == asset.id,
        AuditResult.check_id.in_(check_ids)
    ).all()

    now = datetime.now(timezone.utc)
    for result in results:
        result.status = status
        result.checked_at = now if status != 'not_checked' else None

    db.session.commit()

    if request.headers.get('HX-Request'):
        all_results = AuditResult.query.filter_by(asset_id=asset.id).all()
        rows_html = ''.join(
            render_template('audits/_result_row.html',
                           result=r, session=session, asset=asset)
            for r in all_results
        )
        stats_html = render_template('audits/_asset_stats.html',
                                     asset=asset, results=all_results, oob=True)
        return rows_html + stats_html

    flash(f'{len(results)} checks updated to {status.replace("_", " ")}.', 'success')
    return redirect(url_for('audits.asset_detail', session_id=session.id, asset_id=asset.id))


@audits_bp.route('/<int:session_id>/complete', methods=['POST'])
@auditor_required
def complete_session(session_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)
    if session.status != 'in_progress':
        flash('Audit must be in progress to complete.', 'error')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    session.status = 'completed'
    session.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    flash('Audit session marked as complete.', 'success')
    return redirect(url_for('audits.session_detail', session_id=session.id))
