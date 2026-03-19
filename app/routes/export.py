from flask import Blueprint, send_file, request, render_template, make_response
from flask_login import login_required, current_user
from ..models import Benchmark, Check
from ..models.audit import AuditSession, AuditAsset, AuditResult
from ..models.hardening import HardeningTask, HardeningCheckResult, HardeningAsset
from ..utils.excel_export import export_benchmark_to_excel, export_audit_to_excel, export_hardening_to_excel
from ..utils.auth import auditor_required, hardening_required

export_bp = Blueprint('export', __name__, url_prefix='/export')


@export_bp.route('/benchmark/<int:benchmark_id>')
@login_required
def export_benchmark(benchmark_id):
    benchmark = Benchmark.query.get_or_404(benchmark_id)

    # Optional filters
    level = request.args.get('level', type=int)
    scored_only = request.args.get('scored_only', 'false') == 'true'

    output = export_benchmark_to_excel(benchmark, level=level, scored_only=scored_only)

    filename = f'CIS_Checklist_{benchmark.platform.slug}_{benchmark.version}.xlsx'
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@export_bp.route('/audit/<int:session_id>')
@auditor_required
def export_audit(session_id):
    from flask import abort
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)

    output = export_audit_to_excel(session)

    title_slug = session.title.replace(' ', '_')[:30]
    date_str = (session.started_at or session.created_at).strftime('%Y%m%d')
    filename = f'Audit_Report_{title_slug}_{date_str}.xlsx'
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@export_bp.route('/hardening/<int:task_id>/excel')
@hardening_required
def export_hardening_excel(task_id):
    from flask import abort
    task = HardeningTask.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        abort(403)

    output = export_hardening_to_excel(task)

    title_slug = task.title.replace(' ', '_')[:30]
    date_str = (task.started_at or task.created_at).strftime('%Y%m%d')
    filename = f'Hardening_Report_{title_slug}_{date_str}.xlsx'
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@export_bp.route('/hardening/<int:task_id>/html')
@hardening_required
def export_hardening_html(task_id):
    from flask import abort
    task = HardeningTask.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        abort(403)

    assets = task.assets.all()
    asset_data = []
    for asset in assets:
        results = HardeningCheckResult.query.filter_by(
            asset_id=asset.id
        ).join(Check).order_by(Check.check_number).all()
        asset_data.append({'asset': asset, 'results': results})

    from datetime import datetime, timezone
    generated_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    html = render_template('hardening/report.html',
                           task=task, asset_data=asset_data,
                           generated_at=generated_at)

    response = make_response(html)
    title_slug = task.title.replace(' ', '_')[:30]
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="Hardening_Report_{title_slug}.html"'
    return response
