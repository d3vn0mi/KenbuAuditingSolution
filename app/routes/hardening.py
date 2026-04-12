from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from ..extensions import db
from ..models import Benchmark, BenchmarkSection, Check
from ..models.hardening import (
    HardeningTask, HardeningAsset, HardeningAssetBenchmark, HardeningCheckResult
)
from ..utils.auth import hardening_required

hardening_bp = Blueprint('hardening', __name__, url_prefix='/hardening')


@hardening_bp.route('/')
@hardening_required
def list_tasks():
    tasks = HardeningTask.query.filter_by(
        user_id=current_user.id
    ).order_by(HardeningTask.created_at.desc()).all()
    return render_template('hardening/list.html', tasks=tasks)


@hardening_bp.route('/new', methods=['GET', 'POST'])
@hardening_required
def new_task():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()

        if not title:
            flash('Title is required.', 'error')
            return render_template('hardening/new.html')

        task = HardeningTask(
            user_id=current_user.id,
            title=title,
            description=description or None,
        )
        db.session.add(task)
        db.session.commit()
        flash('Hardening task created.', 'success')
        return redirect(url_for('hardening.task_detail', task_id=task.id))

    return render_template('hardening/new.html')


@hardening_bp.route('/<int:task_id>')
@hardening_required
def task_detail(task_id):
    task = db.get_or_404(HardeningTask, task_id)
    if task.user_id != current_user.id:
        abort(403)
    assets = task.assets.all()
    return render_template('hardening/detail.html', task=task, assets=assets)


@hardening_bp.route('/<int:task_id>/edit', methods=['POST'])
@hardening_required
def edit_task(task_id):
    task = db.get_or_404(HardeningTask, task_id)
    if task.user_id != current_user.id:
        abort(403)
    if task.status != 'draft':
        flash('Cannot edit a task that is not in draft status.', 'error')
        return redirect(url_for('hardening.task_detail', task_id=task.id))

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()

    if not title:
        flash('Title is required.', 'error')
    else:
        task.title = title
        task.description = description or None
        db.session.commit()
        flash('Task updated.', 'success')

    return redirect(url_for('hardening.task_detail', task_id=task.id))


@hardening_bp.route('/<int:task_id>/delete', methods=['POST'])
@hardening_required
def delete_task(task_id):
    task = db.get_or_404(HardeningTask, task_id)
    if task.user_id != current_user.id:
        abort(403)
    if task.status != 'draft':
        flash('Cannot delete a task that is not in draft status.', 'error')
        return redirect(url_for('hardening.task_detail', task_id=task.id))

    db.session.delete(task)
    db.session.commit()
    flash('Hardening task deleted.', 'success')
    return redirect(url_for('hardening.list_tasks'))


@hardening_bp.route('/<int:task_id>/assets/new', methods=['GET', 'POST'])
@hardening_required
def new_asset(task_id):
    task = db.get_or_404(HardeningTask, task_id)
    if task.user_id != current_user.id:
        abort(403)
    if task.status not in ('draft', 'in_progress'):
        flash('Cannot add assets to a completed task.', 'error')
        return redirect(url_for('hardening.task_detail', task_id=task.id))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        asset_type = request.form.get('asset_type', '').strip()
        notes = request.form.get('notes', '').strip()

        if not name or not asset_type:
            flash('Name and type are required.', 'error')
            return render_template('hardening/asset_new.html', task=task)

        asset = HardeningAsset(
            task_id=task.id,
            name=name,
            asset_type=asset_type,
            notes=notes or None,
        )
        db.session.add(asset)
        db.session.commit()
        flash(f'Asset "{name}" added.', 'success')
        return redirect(url_for('hardening.asset_benchmarks', task_id=task.id, asset_id=asset.id))

    return render_template('hardening/asset_new.html', task=task)


@hardening_bp.route('/<int:task_id>/assets/<int:asset_id>/delete', methods=['POST'])
@hardening_required
def delete_asset(task_id, asset_id):
    task = db.get_or_404(HardeningTask, task_id)
    if task.user_id != current_user.id:
        abort(403)
    if task.status not in ('draft', 'in_progress'):
        flash('Cannot remove assets from a completed task.', 'error')
        return redirect(url_for('hardening.task_detail', task_id=task.id))

    asset = db.get_or_404(HardeningAsset, asset_id)
    if asset.task_id != task.id:
        abort(404)

    db.session.delete(asset)
    db.session.commit()
    flash(f'Asset "{asset.name}" removed.', 'success')
    return redirect(url_for('hardening.task_detail', task_id=task.id))


@hardening_bp.route('/<int:task_id>/assets/<int:asset_id>/benchmarks', methods=['GET', 'POST'])
@hardening_required
def asset_benchmarks(task_id, asset_id):
    task = db.get_or_404(HardeningTask, task_id)
    if task.user_id != current_user.id:
        abort(403)
    if task.status not in ('draft', 'in_progress'):
        flash('Cannot modify benchmarks on a completed task.', 'error')
        return redirect(url_for('hardening.task_detail', task_id=task.id))

    asset = db.get_or_404(HardeningAsset, asset_id)
    if asset.task_id != task.id:
        abort(404)

    if request.method == 'POST':
        selected_ids = request.form.getlist('benchmark_ids', type=int)

        # Remove existing assignments
        HardeningAssetBenchmark.query.filter_by(asset_id=asset.id).delete()

        # Add new assignments
        for bid in selected_ids:
            mapping = HardeningAssetBenchmark(asset_id=asset.id, benchmark_id=bid)
            db.session.add(mapping)

        # If task is in_progress, regenerate check results for this asset
        if task.status == 'in_progress':
            HardeningCheckResult.query.filter_by(asset_id=asset.id).delete()
            _generate_check_results_for_asset(asset)

        db.session.commit()
        flash(f'Benchmarks updated for "{asset.name}".', 'success')
        return redirect(url_for('hardening.task_detail', task_id=task.id))

    benchmarks = Benchmark.query.order_by(Benchmark.name).all()
    assigned_ids = {ab.benchmark_id for ab in asset.benchmarks}
    return render_template('hardening/asset_benchmarks.html',
                           task=task, asset=asset,
                           benchmarks=benchmarks, assigned_ids=assigned_ids)


def _generate_check_results_for_asset(asset):
    """Generate HardeningCheckResult records for all checks in the asset's benchmarks."""
    benchmark_ids = [ab.benchmark_id for ab in asset.benchmarks]
    if not benchmark_ids:
        return 0
    checks = Check.query.join(BenchmarkSection).filter(
        BenchmarkSection.benchmark_id.in_(benchmark_ids)
    ).all()
    for check in checks:
        result = HardeningCheckResult(asset_id=asset.id, check_id=check.id)
        db.session.add(result)
    return len(checks)


@hardening_bp.route('/<int:task_id>/start', methods=['POST'])
@hardening_required
def start_task(task_id):
    task = db.get_or_404(HardeningTask, task_id)
    if task.user_id != current_user.id:
        abort(403)
    if task.status != 'draft':
        flash('Task is already started.', 'error')
        return redirect(url_for('hardening.task_detail', task_id=task.id))

    assets = task.assets.all()
    if not assets:
        flash('Add at least one asset before starting.', 'error')
        return redirect(url_for('hardening.task_detail', task_id=task.id))

    # Validate that each asset has at least one benchmark
    for asset in assets:
        if not asset.benchmarks:
            flash(f'Asset "{asset.name}" has no benchmarks assigned.', 'error')
            return redirect(url_for('hardening.task_detail', task_id=task.id))

    # Generate check results for all assets
    total_checks = 0
    for asset in assets:
        total_checks += _generate_check_results_for_asset(asset)

    task.status = 'in_progress'
    task.started_at = datetime.now(timezone.utc)
    db.session.commit()
    flash(f'Hardening task started with {total_checks} checks across {len(assets)} assets.', 'success')
    return redirect(url_for('hardening.task_detail', task_id=task.id))


@hardening_bp.route('/<int:task_id>/assets/<int:asset_id>')
@hardening_required
def asset_detail(task_id, asset_id):
    task = db.get_or_404(HardeningTask, task_id)
    if task.user_id != current_user.id:
        abort(403)

    asset = db.get_or_404(HardeningAsset, asset_id)
    if asset.task_id != task.id:
        abort(404)

    results = HardeningCheckResult.query.filter_by(
        asset_id=asset.id
    ).join(Check).order_by(Check.check_number).all()

    return render_template('hardening/asset_detail.html',
                           task=task, asset=asset, results=results)


@hardening_bp.route('/<int:task_id>/assets/<int:asset_id>/check/<int:check_id>', methods=['POST'])
@hardening_required
def update_check(task_id, asset_id, check_id):
    task = db.get_or_404(HardeningTask, task_id)
    if task.user_id != current_user.id:
        abort(403)

    result = HardeningCheckResult.query.filter_by(
        asset_id=asset_id,
        check_id=check_id
    ).first_or_404()

    if result.asset.task_id != task.id:
        abort(404)

    status = request.form.get('status', 'pending')
    notes = request.form.get('notes', '').strip()

    if status in ('pending', 'done', 'skipped'):
        result.status = status
        result.notes = notes or None
        result.completed_at = datetime.now(timezone.utc) if status != 'pending' else None
        db.session.commit()

    if request.headers.get('HX-Request'):
        asset = result.asset
        results = HardeningCheckResult.query.filter_by(asset_id=asset.id).all()
        row_html = render_template('hardening/_check_row.html',
                                   result=result, task=task, asset=asset)
        stats_html = render_template('hardening/_asset_stats.html',
                                     asset=asset, results=results, oob=True)
        return row_html + stats_html

    return redirect(url_for('hardening.asset_detail', task_id=task.id, asset_id=asset_id))


@hardening_bp.route('/<int:task_id>/assets/<int:asset_id>/bulk-update', methods=['POST'])
@hardening_required
def bulk_update_checks(task_id, asset_id):
    task = db.get_or_404(HardeningTask, task_id)
    if task.user_id != current_user.id:
        abort(403)
    if task.status != 'in_progress':
        flash('Task must be in progress to update checks.', 'error')
        return redirect(url_for('hardening.task_detail', task_id=task.id))

    asset = db.get_or_404(HardeningAsset, asset_id)
    if asset.task_id != task.id:
        abort(404)

    status = request.form.get('bulk_status', '')
    check_ids = request.form.getlist('check_ids', type=int)

    if status not in ('pending', 'done', 'skipped'):
        flash('Invalid status.', 'error')
        return redirect(url_for('hardening.asset_detail', task_id=task.id, asset_id=asset.id))

    if not check_ids:
        flash('No checks selected.', 'error')
        return redirect(url_for('hardening.asset_detail', task_id=task.id, asset_id=asset.id))

    results = HardeningCheckResult.query.filter(
        HardeningCheckResult.asset_id == asset.id,
        HardeningCheckResult.check_id.in_(check_ids)
    ).all()

    now = datetime.now(timezone.utc)
    for result in results:
        result.status = status
        result.completed_at = now if status != 'pending' else None

    db.session.commit()
    flash(f'{len(results)} checks updated to {status}.', 'success')
    return redirect(url_for('hardening.asset_detail', task_id=task.id, asset_id=asset.id))


@hardening_bp.route('/<int:task_id>/complete', methods=['POST'])
@hardening_required
def complete_task(task_id):
    task = db.get_or_404(HardeningTask, task_id)
    if task.user_id != current_user.id:
        abort(403)
    if task.status != 'in_progress':
        flash('Task must be in progress to complete.', 'error')
        return redirect(url_for('hardening.task_detail', task_id=task.id))

    task.status = 'completed'
    task.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    flash('Hardening task marked as complete.', 'success')
    return redirect(url_for('hardening.task_detail', task_id=task.id))
