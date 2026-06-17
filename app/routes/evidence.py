import io
from datetime import date
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, send_file)
from flask_login import current_user
from ..extensions import db
from ..models import Control, Evidence, EvidenceVersion
from ..models.evidence import EVIDENCE_TYPES
from ..utils.auth import compliance_required, compliance_view_required
from ..utils import evidence_store, crypto

evidence_bp = Blueprint('evidence', __name__, url_prefix='/evidence')


def _authorize(evidence):
    """Access hook. Single-tenant MVP: compliance_required already gates access.
    When multi-tenancy lands, check evidence.organization_id against the user's
    organization here so this is not a retrofit."""
    return True


def _parse_date(value):
    value = (value or '').strip()
    return date.fromisoformat(value) if value else None


def _add_version(evidence, file_storage, note=None):
    data = file_storage.read()
    if not data:
        return None
    meta = evidence_store.save_evidence_file(data, file_storage.filename or 'upload')
    next_version = (evidence.versions.first().version + 1) if evidence.versions.first() else 1
    ev = EvidenceVersion(
        evidence_id=evidence.id,
        version=next_version,
        content_hash=meta['content_hash'],
        storage_name=meta['storage_name'],
        original_filename=meta['original_filename'],
        mime=file_storage.mimetype,
        size=meta['size'],
        note=note,
    )
    db.session.add(ev)
    return ev


@evidence_bp.route('/')
@compliance_view_required
def list_evidence():
    items = Evidence.query.order_by(Evidence.created_at.desc()).all()
    return render_template('evidence/list.html', items=items)


@evidence_bp.route('/new', methods=['GET', 'POST'])
@compliance_required
def new_evidence():
    controls = Control.query.order_by(Control.code).all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Title is required.', 'error')
            return render_template('evidence/new.html', controls=controls,
                                   evidence_types=EVIDENCE_TYPES)

        evidence = Evidence(
            title=title,
            description=request.form.get('description', '').strip() or None,
            evidence_type=request.form.get('evidence_type', 'document'),
            owner_id=current_user.id,
            valid_until=_parse_date(request.form.get('valid_until')),
            review_date=_parse_date(request.form.get('review_date')),
        )
        control_ids = request.form.getlist('control_ids', type=int)
        if control_ids:
            evidence.controls = Control.query.filter(Control.id.in_(control_ids)).all()
        db.session.add(evidence)
        db.session.flush()

        file_storage = request.files.get('file')
        if file_storage and file_storage.filename:
            _add_version(evidence, file_storage)

        db.session.commit()
        flash('Evidence added.', 'success')
        return redirect(url_for('evidence.evidence_detail', evidence_id=evidence.id))

    return render_template('evidence/new.html', controls=controls,
                           evidence_types=EVIDENCE_TYPES)


@evidence_bp.route('/<int:evidence_id>')
@compliance_view_required
def evidence_detail(evidence_id):
    evidence = db.get_or_404(Evidence, evidence_id)
    if not _authorize(evidence):
        abort(403)
    return render_template('evidence/detail.html', evidence=evidence)


@evidence_bp.route('/<int:evidence_id>/version', methods=['POST'])
@compliance_required
def add_version(evidence_id):
    evidence = db.get_or_404(Evidence, evidence_id)
    if not _authorize(evidence):
        abort(403)
    file_storage = request.files.get('file')
    if not (file_storage and file_storage.filename):
        flash('Choose a file to upload.', 'error')
        return redirect(url_for('evidence.evidence_detail', evidence_id=evidence.id))
    _add_version(evidence, file_storage, note=request.form.get('note', '').strip() or None)
    db.session.commit()
    flash('New version uploaded.', 'success')
    return redirect(url_for('evidence.evidence_detail', evidence_id=evidence.id))


@evidence_bp.route('/<int:evidence_id>/version/<int:version_id>/download')
@compliance_view_required
def download_version(evidence_id, version_id):
    evidence = db.get_or_404(Evidence, evidence_id)
    if not _authorize(evidence):
        abort(403)
    version = db.get_or_404(EvidenceVersion, version_id)
    if version.evidence_id != evidence.id:
        abort(404)

    data = evidence_store.load_evidence_file(version.storage_name)  # raises if tampered
    # Integrity check before serving — proves the file is what was uploaded.
    if crypto.sha256_hex(data) != version.content_hash:
        abort(409)  # integrity mismatch
    return send_file(
        io.BytesIO(data),
        mimetype=version.mime or 'application/octet-stream',
        as_attachment=True,
        download_name=version.original_filename or f'evidence-{version.id}',
    )


@evidence_bp.route('/<int:evidence_id>/delete', methods=['POST'])
@compliance_required
def delete_evidence(evidence_id):
    evidence = db.get_or_404(Evidence, evidence_id)
    if not _authorize(evidence):
        abort(403)
    for version in evidence.versions.all():
        evidence_store.delete_evidence_file(version.storage_name)
    db.session.delete(evidence)
    db.session.commit()
    flash('Evidence deleted.', 'success')
    return redirect(url_for('evidence.list_evidence'))
