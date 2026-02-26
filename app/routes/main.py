from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..models import Platform, Benchmark, Check, AuditSession

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

    return render_template('main/dashboard.html',
                           platforms=platforms,
                           benchmarks=benchmarks,
                           total_checks=total_checks,
                           recent_audits=recent_audits)
