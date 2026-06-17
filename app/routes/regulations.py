from flask import Blueprint, render_template
from flask_login import login_required
from ..models import Regulation, Obligation, Control

regulations_bp = Blueprint('regulations', __name__, url_prefix='/regulations')


@regulations_bp.route('/')
@login_required
def list_regulations():
    regulations = Regulation.query.order_by(Regulation.short_code).all()
    rows = []
    for reg in regulations:
        control_ids = set()
        for ob in reg.obligations:
            control_ids.update(c.id for c in ob.controls)
        rows.append({
            'reg': reg,
            'obligations': reg.obligations.count(),
            'controls': len(control_ids),
        })
    return render_template('regulations/list.html', rows=rows)


@regulations_bp.route('/<slug>')
@login_required
def regulation_detail(slug):
    reg = Regulation.query.filter_by(slug=slug).first_or_404()
    top = reg.obligations.filter_by(parent_id=None).order_by(Obligation.sort_order).all()
    return render_template('regulations/detail.html', regulation=reg, obligations=top)


@regulations_bp.route('/controls/<code>')
@login_required
def control_detail(code):
    control = Control.query.filter_by(code=code).first_or_404()
    return render_template('regulations/control.html', control=control)
