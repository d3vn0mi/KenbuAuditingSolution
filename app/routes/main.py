from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Platform, Benchmark, Check, AuditSession
from ..models.hardening import HardeningTask
from ..models.pentest import PentestAssessment, PentestTeamMember

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    platforms = Platform.query.order_by(Platform.name).all()
    benchmarks = Benchmark.query.all()
    total_checks = Check.query.count()

    recent_audits = []
    my_pentests = []
    my_hardening = []

    if current_user.can_audit:
        recent_audits = AuditSession.query.filter_by(
            user_id=current_user.id
        ).order_by(AuditSession.created_at.desc()).limit(5).all()

    if current_user.can_harden:
        my_hardening = HardeningTask.query.filter_by(
            user_id=current_user.id
        ).order_by(HardeningTask.created_at.desc()).limit(5).all()

    if current_user.can_pentest:
        # Pentests: owned + team member
        owned_pentests = PentestAssessment.query.filter_by(user_id=current_user.id)
        member_ids = db.session.query(PentestTeamMember.assessment_id).filter_by(
            user_id=current_user.id
        )
        team_pentests = PentestAssessment.query.filter(PentestAssessment.id.in_(member_ids.scalar_subquery()))
        my_pentests = owned_pentests.union(team_pentests).order_by(
            PentestAssessment.created_at.desc()
        ).limit(5).all()

    # Admin: all audits and hardening tasks across users
    all_audits = None
    all_hardening = None
    if current_user.is_admin:
        all_audits = AuditSession.query.order_by(
            AuditSession.created_at.desc()
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
                           my_pentests=my_pentests,
                           all_audits=all_audits,
                           all_hardening=all_hardening)
