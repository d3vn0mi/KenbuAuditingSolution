from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from ..extensions import db
from ..models.user import User

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/users')
@admin_required
def users():
    pending = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).all()
    approved = User.query.filter_by(is_approved=True).order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', pending=pending, approved=approved)


@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    user.is_approved = True
    db.session.commit()
    flash(f'User "{user.username}" has been approved.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@admin_required
def reject_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash('You cannot remove yourself.', 'error')
        return redirect(url_for('admin.users'))
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{username}" has been rejected and removed.', 'info')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle-role', methods=['POST'])
@admin_required
def toggle_role(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash('You cannot change your own role.', 'error')
        return redirect(url_for('admin.users'))
    user.role = 'user' if user.role == 'admin' else 'admin'
    db.session.commit()
    flash(f'User "{user.username}" is now {user.role}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/revoke', methods=['POST'])
@admin_required
def revoke_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash('You cannot revoke your own access.', 'error')
        return redirect(url_for('admin.users'))
    user.is_approved = False
    db.session.commit()
    flash(f'Access revoked for "{user.username}".', 'info')
    return redirect(url_for('admin.users'))


@admin_bp.route('/change-password', methods=['GET', 'POST'])
@admin_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
        elif not new_password:
            flash('New password is required.', 'error')
        elif len(new_password) < 8:
            flash('New password must be at least 8 characters.', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'error')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect(url_for('admin.users'))

    return render_template('admin/change_password.html')
