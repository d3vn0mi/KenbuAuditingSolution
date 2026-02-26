from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Benchmark, BenchmarkSection, Check, AuditSession, AuditResult

audits_bp = Blueprint('audits', __name__, url_prefix='/audits')


@audits_bp.route('/')
@login_required
def list_audits():
    sessions = AuditSession.query.filter_by(
        user_id=current_user.id
    ).order_by(AuditSession.started_at.desc()).all()
    return render_template('audits/list.html', sessions=sessions)


@audits_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_audit():
    if request.method == 'POST':
        benchmark_id = request.form.get('benchmark_id', type=int)
        target_name = request.form.get('target_name', '').strip()
        target_ip = request.form.get('target_ip', '').strip()
        notes = request.form.get('notes', '').strip()

        if not benchmark_id:
            flash('Please select a benchmark.', 'error')
            benchmarks = Benchmark.query.order_by(Benchmark.name).all()
            return render_template('audits/new.html', benchmarks=benchmarks)

        benchmark = Benchmark.query.get_or_404(benchmark_id)

        # Create session
        session = AuditSession(
            user_id=current_user.id,
            benchmark_id=benchmark_id,
            target_name=target_name or 'Unnamed Target',
            target_ip=target_ip,
            notes=notes
        )
        db.session.add(session)
        db.session.flush()

        # Create audit result entries for all checks in benchmark
        checks = Check.query.join(BenchmarkSection).filter(
            BenchmarkSection.benchmark_id == benchmark_id
        ).all()
        for check in checks:
            result = AuditResult(
                session_id=session.id,
                check_id=check.id
            )
            db.session.add(result)

        db.session.commit()
        flash(f'Audit session created with {len(checks)} checks.', 'success')
        return redirect(url_for('audits.session_detail', session_id=session.id))

    benchmarks = Benchmark.query.order_by(Benchmark.name).all()
    return render_template('audits/new.html', benchmarks=benchmarks)


@audits_bp.route('/<int:session_id>')
@login_required
def session_detail(session_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)

    # Get results with checks, organized by section
    results = AuditResult.query.filter_by(
        session_id=session_id
    ).join(Check).order_by(Check.check_number).all()

    return render_template('audits/session.html',
                           session=session,
                           results=results)


@audits_bp.route('/<int:session_id>/check/<int:check_id>', methods=['POST'])
@login_required
def update_result(session_id, check_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)

    result = AuditResult.query.filter_by(
        session_id=session_id,
        check_id=check_id
    ).first_or_404()

    status = request.form.get('status', 'not_checked')
    finding = request.form.get('finding', '').strip()

    if status in ('pass', 'fail', 'not_applicable', 'not_checked'):
        result.status = status
        result.finding = finding
        result.checked_at = datetime.now(timezone.utc) if status != 'not_checked' else None
        db.session.commit()

    # Return HTMX partial
    if request.headers.get('HX-Request'):
        return render_template('audits/_result_row.html',
                               result=result, session=session)

    return redirect(url_for('audits.session_detail', session_id=session_id))


@audits_bp.route('/<int:session_id>/complete', methods=['POST'])
@login_required
def complete_session(session_id):
    session = AuditSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)

    session.status = 'completed'
    session.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    flash('Audit session marked as complete.', 'success')
    return redirect(url_for('audits.session_detail', session_id=session_id))
