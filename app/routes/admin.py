from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import current_user
from ..extensions import db
from ..models.user import User, VALID_ROLES
from ..models import ActivityLog
from ..utils.auth import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users')
@admin_required
def users():
    pending = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).all()
    approved = User.query.filter_by(is_approved=True).order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', pending=pending, approved=approved)


@admin_bp.route('/activity')
@admin_required
def activity():
    entries = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(200).all()
    return render_template('admin/activity.html', entries=entries)


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


@admin_bp.route('/users/<int:user_id>/set-role', methods=['POST'])
@admin_required
def set_role(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash('You cannot change your own role.', 'error')
        return redirect(url_for('admin.users'))
    new_role = request.form.get('role', '').strip()
    if new_role not in VALID_ROLES:
        flash('Invalid role.', 'error')
        return redirect(url_for('admin.users'))
    user.role = new_role
    db.session.commit()
    flash(f'User "{user.username}" is now {new_role.replace("_", " ")}.', 'success')
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


