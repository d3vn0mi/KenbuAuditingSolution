import io
import csv
import json
from datetime import date
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort)
from ..extensions import db
from ..models import Control, Finding
from ..models.finding import FINDING_SOURCES, FINDING_STATUSES
from ..models.pentest import SEVERITY_LEVELS, PentestFinding
from ..utils.auth import compliance_required, compliance_view_required
from ..utils import findings as findings_service

findings_bp = Blueprint('findings', __name__, url_prefix='/findings')


@findings_bp.route('/')
@compliance_view_required
def list_findings():
    items = Finding.query.order_by(Finding.created_at.desc()).all()
    return render_template('findings/list.html', items=items,
                           SEVERITY_LEVELS=SEVERITY_LEVELS)


@findings_bp.route('/new', methods=['GET', 'POST'])
@compliance_required
def new_finding():
    controls = Control.query.order_by(Control.code).all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Title is required.', 'error')
            return render_template('findings/new.html', controls=controls,
                                   SEVERITY_LEVELS=SEVERITY_LEVELS,
                                   FINDING_SOURCES=FINDING_SOURCES)
        finding = Finding(
            title=title,
            severity=request.form.get('severity', 'informational'),
            source=request.form.get('source', 'internal'),
            status='open',
            description=request.form.get('description', '').strip() or None,
            remediation=request.form.get('remediation', '').strip() or None,
        )
        control_ids = request.form.getlist('control_ids', type=int)
        if control_ids:
            finding.controls = Control.query.filter(Control.id.in_(control_ids)).all()
        db.session.add(finding)
        db.session.commit()
        flash('Finding created.', 'success')
        return redirect(url_for('findings.finding_detail', finding_id=finding.id))

    return render_template('findings/new.html', controls=controls,
                           SEVERITY_LEVELS=SEVERITY_LEVELS, FINDING_SOURCES=FINDING_SOURCES)


@findings_bp.route('/<int:finding_id>')
@compliance_view_required
def finding_detail(finding_id):
    finding = db.get_or_404(Finding, finding_id)
    controls = Control.query.order_by(Control.code).all()
    return render_template('findings/detail.html', finding=finding, controls=controls,
                           FINDING_STATUSES=FINDING_STATUSES)


@findings_bp.route('/<int:finding_id>/update', methods=['POST'])
@compliance_required
def update_finding(finding_id):
    finding = db.get_or_404(Finding, finding_id)
    status = request.form.get('status')
    if status in FINDING_STATUSES:
        finding.status = status
    if 'control_ids' in request.form:
        control_ids = request.form.getlist('control_ids', type=int)
        finding.controls = Control.query.filter(Control.id.in_(control_ids)).all()
    db.session.commit()
    flash('Finding updated.', 'success')
    return redirect(url_for('findings.finding_detail', finding_id=finding.id))


@findings_bp.route('/import', methods=['GET', 'POST'])
@compliance_required
def import_findings():
    if request.method == 'POST':
        file_storage = request.files.get('file')
        if not (file_storage and file_storage.filename):
            flash('Choose a JSON or CSV file.', 'error')
            return render_template('findings/import.html')
        raw = file_storage.read().decode('utf-8', errors='replace')
        name = file_storage.filename.lower()
        try:
            if name.endswith('.json'):
                data = json.loads(raw)
                rows = data if isinstance(data, list) else data.get('findings', [])
            else:  # CSV
                reader = csv.DictReader(io.StringIO(raw))
                rows = []
                for r in reader:
                    if r.get('controls'):
                        r['controls'] = [c.strip() for c in r['controls'].split(';') if c.strip()]
                    rows.append(r)
        except (ValueError, KeyError) as exc:
            flash(f'Could not parse file: {exc}', 'error')
            return render_template('findings/import.html')

        created = findings_service.import_findings(rows)
        flash(f'Imported {len(created)} findings.', 'success')
        return redirect(url_for('findings.list_findings'))

    return render_template('findings/import.html')


@findings_bp.route('/promote/<int:pentest_finding_id>', methods=['POST'])
@compliance_required
def promote(pentest_finding_id):
    pf = db.get_or_404(PentestFinding, pentest_finding_id)
    finding = findings_service.promote_pentest_finding(pf)
    flash('Pentest finding promoted to a control-linkable finding.', 'success')
    return redirect(url_for('findings.finding_detail', finding_id=finding.id))
