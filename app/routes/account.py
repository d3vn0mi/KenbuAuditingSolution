import io
import base64
import pyotp
import qrcode
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from ..extensions import db

account_bp = Blueprint('account', __name__, url_prefix='/account')


@account_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
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
            return redirect(url_for('main.dashboard'))

    return render_template('account/change_password.html')


@account_bp.route('/mfa/setup', methods=['GET', 'POST'])
@login_required
def mfa_setup():
    if current_user.mfa_enabled:
        flash('MFA is already enabled on your account.', 'info')
        return redirect(url_for('account.mfa_settings'))

    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        secret = session.get('mfa_setup_secret')

        if not secret:
            flash('MFA setup session expired. Please try again.', 'error')
            return redirect(url_for('account.mfa_setup'))

        totp = pyotp.TOTP(secret)
        if totp.verify(token, valid_window=1):
            current_user.mfa_secret = secret
            current_user.mfa_enabled = True
            db.session.commit()
            session.pop('mfa_setup_secret', None)
            flash('MFA has been enabled successfully.', 'success')
            return redirect(url_for('account.mfa_settings'))
        else:
            flash('Invalid verification code. Please try again.', 'error')

    secret = pyotp.random_base32()
    session['mfa_setup_secret'] = secret
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.username, issuer_name='Kenbu')

    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template('account/mfa_setup.html', secret=secret, qr_code=qr_base64)


@account_bp.route('/mfa/disable', methods=['POST'])
@login_required
def mfa_disable():
    token = request.form.get('token', '').strip()

    if not current_user.mfa_enabled:
        flash('MFA is not enabled on your account.', 'info')
        return redirect(url_for('account.mfa_settings'))

    if not current_user.verify_mfa_token(token):
        flash('Invalid verification code. MFA was not disabled.', 'error')
        return redirect(url_for('account.mfa_settings'))

    current_user.mfa_secret = None
    current_user.mfa_enabled = False
    db.session.commit()
    flash('MFA has been disabled.', 'success')
    return redirect(url_for('account.mfa_settings'))


@account_bp.route('/mfa', methods=['GET'])
@login_required
def mfa_settings():
    return render_template('account/mfa_settings.html')
