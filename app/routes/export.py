from flask import Blueprint, send_file, request
from flask_login import login_required, current_user
from ..models import Benchmark, AuditSession
from ..utils.excel_export import export_benchmark_to_excel, export_audit_to_excel

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
@login_required
def export_audit(session_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        from flask import abort
        abort(403)

    output = export_audit_to_excel(session)

    target = session.target_name.replace(' ', '_') if session.target_name else 'audit'
    filename = f'Audit_Report_{target}_{session.started_at.strftime("%Y%m%d")}.xlsx'
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
