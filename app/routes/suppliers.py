from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort)
from ..extensions import db
from ..models import Supplier, SBOM, Control
from ..models.supplier import SUPPLIER_CRITICALITY, SUPPLIER_STATUSES
from ..utils.auth import compliance_required, compliance_view_required
from ..utils import sbom as sbom_util

suppliers_bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')


@suppliers_bp.route('/')
@compliance_view_required
def list_suppliers():
    items = Supplier.query.order_by(Supplier.name).all()
    return render_template('suppliers/list.html', items=items)


@suppliers_bp.route('/new', methods=['GET', 'POST'])
@compliance_required
def new_supplier():
    controls = Control.query.filter_by(domain='SupplyChain').order_by(Control.code).all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Name is required.', 'error')
            return render_template('suppliers/new.html', controls=controls,
                                   criticality=SUPPLIER_CRITICALITY)
        supplier = Supplier(
            name=name,
            contact=request.form.get('contact', '').strip() or None,
            country=request.form.get('country', '').strip() or None,
            criticality=request.form.get('criticality', 'medium'),
            description=request.form.get('description', '').strip() or None,
            status='under_review',
        )
        control_ids = request.form.getlist('control_ids', type=int)
        if control_ids:
            supplier.controls = Control.query.filter(Control.id.in_(control_ids)).all()
        db.session.add(supplier)
        db.session.commit()
        flash('Supplier added.', 'success')
        return redirect(url_for('suppliers.supplier_detail', supplier_id=supplier.id))
    return render_template('suppliers/new.html', controls=controls,
                           criticality=SUPPLIER_CRITICALITY)


@suppliers_bp.route('/<int:supplier_id>')
@compliance_view_required
def supplier_detail(supplier_id):
    supplier = db.get_or_404(Supplier, supplier_id)
    return render_template('suppliers/detail.html', supplier=supplier,
                           statuses=SUPPLIER_STATUSES, sboms=supplier.sboms.all())


@suppliers_bp.route('/<int:supplier_id>/update', methods=['POST'])
@compliance_required
def update_supplier(supplier_id):
    supplier = db.get_or_404(Supplier, supplier_id)
    status = request.form.get('status')
    if status in SUPPLIER_STATUSES:
        supplier.status = status
    db.session.commit()
    flash('Supplier updated.', 'success')
    return redirect(url_for('suppliers.supplier_detail', supplier_id=supplier.id))


@suppliers_bp.route('/<int:supplier_id>/sbom', methods=['POST'])
@compliance_required
def upload_sbom(supplier_id):
    supplier = db.get_or_404(Supplier, supplier_id)
    file_storage = request.files.get('file')
    if not (file_storage and file_storage.filename):
        flash('Choose an SBOM JSON file.', 'error')
        return redirect(url_for('suppliers.supplier_detail', supplier_id=supplier.id))
    raw = file_storage.read()
    try:
        sbom = sbom_util.ingest_sbom(supplier, file_storage.filename, raw)
        db.session.commit()
    except ValueError:
        db.session.rollback()
        flash('Could not parse SBOM (expected CycloneDX or SPDX JSON).', 'error')
        return redirect(url_for('suppliers.supplier_detail', supplier_id=supplier.id))
    flash(f'SBOM ingested ({sbom.component_count} components, {sbom.format}).', 'success')
    return redirect(url_for('suppliers.sbom_detail', supplier_id=supplier.id, sbom_id=sbom.id))


@suppliers_bp.route('/<int:supplier_id>/sbom/<int:sbom_id>')
@compliance_view_required
def sbom_detail(supplier_id, sbom_id):
    supplier = db.get_or_404(Supplier, supplier_id)
    sbom = db.get_or_404(SBOM, sbom_id)
    if sbom.supplier_id != supplier.id:
        abort(404)
    return render_template('suppliers/sbom.html', supplier=supplier, sbom=sbom,
                           components=sbom.components.all())


@suppliers_bp.route('/<int:supplier_id>/delete', methods=['POST'])
@compliance_required
def delete_supplier(supplier_id):
    supplier = db.get_or_404(Supplier, supplier_id)
    db.session.delete(supplier)
    db.session.commit()
    flash('Supplier deleted.', 'success')
    return redirect(url_for('suppliers.list_suppliers'))
