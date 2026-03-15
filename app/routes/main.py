from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..models import Platform, Benchmark, Check, AuditSession
from ..models.hardening import HardeningTask

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    platforms = Platform.query.order_by(Platform.name).all()
    benchmarks = Benchmark.query.all()
    total_checks = Check.query.count()
    recent_audits = AuditSession.query.filter_by(
        user_id=current_user.id
    ).order_by(AuditSession.started_at.desc()).limit(5).all()
    my_hardening = HardeningTask.query.filter_by(
        user_id=current_user.id
    ).order_by(HardeningTask.created_at.desc()).limit(5).all()

    # Admin: all audits and hardening tasks across users
    all_audits = None
    all_hardening = None
    if current_user.is_admin:
        all_audits = AuditSession.query.order_by(
            AuditSession.started_at.desc()
        ).limit(10).all()
        all_hardening = HardeningTask.query.order_by(
            HardeningTask.created_at.desc()
        ).limit(10).all()

    return render_template('main/dashboard.html',
                           platforms=platforms,
                           benchmarks=benchmarks,
                           total_checks=total_checks,
                           recent_audits=recent_audits,
                           my_hardening=my_hardening,
                           all_audits=all_audits,
                           all_hardening=all_hardening)
