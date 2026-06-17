from datetime import datetime, timezone
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort)
from ..extensions import db
from ..models import Incident, Regulation
from ..models.incident import INCIDENT_SEVERITIES, INCIDENT_STATUSES
from ..utils.auth import compliance_required
from ..utils import incidents as inc_service

incidents_bp = Blueprint('incidents', __name__, url_prefix='/incidents')

_STAGE_FIELDS = {
    'early_warning': 'early_warning_sent_at',
    'notification': 'notification_sent_at',
    'final_report': 'final_report_sent_at',
}


def _parse_dt(value):
    value = (value or '').strip()
    if not value:
        return None
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@incidents_bp.route('/')
@compliance_required
def list_incidents():
    items = Incident.query.order_by(Incident.detected_at.desc()).all()
    rows = [{'i': i, 'overdue': inc_service.overdue_stage_count(i)} for i in items]
    return render_template('incidents/list.html', rows=rows)


@incidents_bp.route('/new', methods=['GET', 'POST'])
@compliance_required
def new_incident():
    regulations = Regulation.query.order_by(Regulation.short_code).all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        detected_at = _parse_dt(request.form.get('detected_at'))
        if not title or not detected_at:
            flash('Title and detection time are required.', 'error')
            return render_template('incidents/new.html', regulations=regulations,
                                   severities=INCIDENT_SEVERITIES)
        incident = Incident(
            title=title,
            severity=request.form.get('severity', 'high'),
            description=request.form.get('description', '').strip() or None,
            affected_systems=request.form.get('affected_systems', '').strip() or None,
            detected_at=detected_at,
            regulation_id=request.form.get('regulation_id', type=int) or None,
            status='open',
        )
        db.session.add(incident)
        db.session.commit()
        flash('Incident logged. Statutory clock started.', 'success')
        return redirect(url_for('incidents.incident_detail', incident_id=incident.id))
    return render_template('incidents/new.html', regulations=regulations,
                           severities=INCIDENT_SEVERITIES)


@incidents_bp.route('/<int:incident_id>')
@compliance_required
def incident_detail(incident_id):
    incident = db.get_or_404(Incident, incident_id)
    clock = inc_service.incident_clock(incident)
    return render_template('incidents/detail.html', incident=incident, clock=clock,
                           statuses=INCIDENT_STATUSES)


@incidents_bp.route('/<int:incident_id>/stage/<stage>/sent', methods=['POST'])
@compliance_required
def mark_stage_sent(incident_id, stage):
    incident = db.get_or_404(Incident, incident_id)
    field = _STAGE_FIELDS.get(stage)
    if not field:
        abort(404)
    setattr(incident, field, datetime.now(timezone.utc))
    db.session.commit()
    flash(f'{stage.replace("_", " ").title()} marked as sent.', 'success')
    return redirect(url_for('incidents.incident_detail', incident_id=incident.id))


@incidents_bp.route('/<int:incident_id>/update', methods=['POST'])
@compliance_required
def update_incident(incident_id):
    incident = db.get_or_404(Incident, incident_id)
    status = request.form.get('status')
    if status in INCIDENT_STATUSES:
        incident.status = status
    db.session.commit()
    flash('Incident updated.', 'success')
    return redirect(url_for('incidents.incident_detail', incident_id=incident.id))


@incidents_bp.route('/<int:incident_id>/report/<stage>')
@compliance_required
def report(incident_id, stage):
    incident = db.get_or_404(Incident, incident_id)
    if stage not in _STAGE_FIELDS:
        abort(404)
    labels = {
        'early_warning': 'Early Warning (NIS2 Art. 23(4)(a))',
        'notification': 'Incident Notification (NIS2 Art. 23(4)(b))',
        'final_report': 'Final Report (NIS2 Art. 23(4)(d))',
    }
    return render_template('incidents/report.html', incident=incident,
                           stage=stage, stage_label=labels[stage])


@incidents_bp.route('/<int:incident_id>/delete', methods=['POST'])
@compliance_required
def delete_incident(incident_id):
    incident = db.get_or_404(Incident, incident_id)
    db.session.delete(incident)
    db.session.commit()
    flash('Incident deleted.', 'success')
    return redirect(url_for('incidents.list_incidents'))
