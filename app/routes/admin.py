import io
import base64
from functools import wraps
import pyotp
import qrcode
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, session
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


@admin_bp.route('/mfa/setup', methods=['GET', 'POST'])
@admin_required
def mfa_setup():
    if current_user.mfa_enabled:
        flash('MFA is already enabled on your account.', 'info')
        return redirect(url_for('admin.users'))

    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        secret = session.get('mfa_setup_secret')

        if not secret:
            flash('MFA setup session expired. Please try again.', 'error')
            return redirect(url_for('admin.mfa_setup'))

        # Verify the token against the session secret without modifying user object
        totp = pyotp.TOTP(secret)
        if totp.verify(token, valid_window=1):
            current_user.mfa_secret = secret
            current_user.mfa_enabled = True
            db.session.commit()
            session.pop('mfa_setup_secret', None)
            flash('MFA has been enabled successfully.', 'success')
            return redirect(url_for('admin.users'))
        else:
            flash('Invalid verification code. Please try again.', 'error')

    # Generate a new secret and QR code
    secret = pyotp.random_base32()
    session['mfa_setup_secret'] = secret
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.username, issuer_name='Kenbu')

    # Generate QR code as base64 image
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template('admin/mfa_setup.html', secret=secret, qr_code=qr_base64)


@admin_bp.route('/mfa/disable', methods=['POST'])
@admin_required
def mfa_disable():
    token = request.form.get('token', '').strip()

    if not current_user.mfa_enabled:
        flash('MFA is not enabled on your account.', 'info')
        return redirect(url_for('admin.users'))

    if not current_user.verify_mfa_token(token):
        flash('Invalid verification code. MFA was not disabled.', 'error')
        return redirect(url_for('admin.mfa_settings'))

    current_user.mfa_secret = None
    current_user.mfa_enabled = False
    db.session.commit()
    flash('MFA has been disabled.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/mfa', methods=['GET'])
@admin_required
def mfa_settings():
    return render_template('admin/mfa_settings.html')
