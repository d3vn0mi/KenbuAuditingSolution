import io
from datetime import date, datetime, timezone
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, send_file)
from flask_login import current_user
from ..extensions import db
from ..models import Regulation, Control, ReadinessAssessment, ControlStatus
from ..models.readiness import CONTROL_STATUSES
from ..utils.auth import compliance_required, compliance_view_required
from ..utils import readiness as scoring
from ..utils import pack as pack_util
from ..utils.excel_export import export_readiness_to_excel

readiness_bp = Blueprint('readiness', __name__, url_prefix='/readiness')


def _controls_for_regulation(reg):
    """Controls mapped to a regulation's obligations (or all controls if reg is None)."""
    if reg is None:
        return Control.query.order_by(Control.code).all()
    ids = set()
    for ob in reg.obligations:
        ids.update(c.id for c in ob.controls)
    if not ids:
        return []
    return Control.query.filter(Control.id.in_(ids)).order_by(Control.code).all()


def _summary(a):
    sevs = scoring.open_finding_severities(a)  # finding impact on readiness
    return {
        'overall': scoring.assessment_score(a, finding_severities=sevs),
        'domains': scoring.domain_scores(a, finding_severities=sevs),
        'coverage': (scoring.obligation_coverage(a, a.regulation, finding_severities=sevs)
                     if a.regulation else None),
        'roadmap': scoring.remediation_roadmap(a, finding_severities=sevs),
    }


@readiness_bp.route('/')
@compliance_view_required
def list_assessments():
    assessments = ReadinessAssessment.query.order_by(
        ReadinessAssessment.created_at.desc()).all()
    rows = [{'a': a, 'score': scoring.assessment_score(
        a, finding_severities=scoring.open_finding_severities(a))} for a in assessments]
    return render_template('readiness/list.html', rows=rows)


@readiness_bp.route('/new', methods=['GET', 'POST'])
@compliance_required
def new_assessment():
    regulations = Regulation.query.order_by(Regulation.short_code).all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        regulation_id = request.form.get('regulation_id', type=int)
        if not title:
            flash('Title is required.', 'error')
            return render_template('readiness/new.html', regulations=regulations)

        reg = db.session.get(Regulation, regulation_id) if regulation_id else None
        assessment = ReadinessAssessment(
            title=title,
            regulation_id=reg.id if reg else None,
            owner_id=current_user.id,
            status='active',
        )
        db.session.add(assessment)
        db.session.flush()

        for control in _controls_for_regulation(reg):
            db.session.add(ControlStatus(
                assessment_id=assessment.id, control_id=control.id, status='not_started'))
        db.session.commit()
        flash('Readiness assessment created.', 'success')
        return redirect(url_for('readiness.assessment_detail', assessment_id=assessment.id))

    return render_template('readiness/new.html', regulations=regulations)


@readiness_bp.route('/<int:assessment_id>')
@compliance_view_required
def assessment_detail(assessment_id):
    a = db.get_or_404(ReadinessAssessment, assessment_id)
    statuses = a.control_statuses.join(Control).order_by(
        Control.domain, Control.code).all()
    return render_template('readiness/detail.html', a=a, statuses=statuses,
                           CONTROL_STATUSES=CONTROL_STATUSES, **_summary(a))


def _slug(a):
    base = (a.regulation.short_code or a.regulation.slug) if a.regulation else 'cross-reg'
    return f'readiness-{base}-{a.id}'.lower()


@readiness_bp.route('/<int:assessment_id>/export.xlsx')
@compliance_view_required
def export_excel(assessment_id):
    a = db.get_or_404(ReadinessAssessment, assessment_id)
    out = export_readiness_to_excel(a, generated_at=datetime.now(timezone.utc))
    return send_file(
        out, as_attachment=True, download_name=f'{_slug(a)}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@readiness_bp.route('/<int:assessment_id>/export.pdf')
@compliance_view_required
def export_pdf(assessment_id):
    a = db.get_or_404(ReadinessAssessment, assessment_id)
    data = pack_util.render_pdf(a, generated_at=datetime.now(timezone.utc))
    return send_file(
        io.BytesIO(data), as_attachment=True, download_name=f'{_slug(a)}.pdf',
        mimetype='application/pdf')


@readiness_bp.route('/<int:assessment_id>/delete', methods=['POST'])
@compliance_required
def delete_assessment(assessment_id):
    a = db.get_or_404(ReadinessAssessment, assessment_id)
    db.session.delete(a)
    db.session.commit()
    flash('Readiness assessment deleted.', 'success')
    return redirect(url_for('readiness.list_assessments'))


@readiness_bp.route('/<int:assessment_id>/control/<int:control_id>', methods=['POST'])
@compliance_required
def update_control_status(assessment_id, control_id):
    a = db.get_or_404(ReadinessAssessment, assessment_id)
    cs = ControlStatus.query.filter_by(
        assessment_id=a.id, control_id=control_id).first_or_404()

    status = request.form.get('status')
    if status in CONTROL_STATUSES:
        cs.status = status
    cs.maturity = request.form.get('maturity', type=int)
    notes = request.form.get('notes')
    if notes is not None:
        cs.notes = notes.strip() or None
    target = request.form.get('target_date', '').strip()
    cs.target_date = date.fromisoformat(target) if target else None
    db.session.commit()

    if request.headers.get('HX-Request'):
        row = render_template('readiness/_control_row.html', cs=cs, a=a,
                              CONTROL_STATUSES=CONTROL_STATUSES)
        summary = render_template('readiness/_score_summary.html', a=a, oob=True,
                                  **_summary(a))
        return row + summary
    return redirect(url_for('readiness.assessment_detail', assessment_id=a.id))
