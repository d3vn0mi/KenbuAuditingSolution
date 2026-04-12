from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db, limiter
from ..models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def _is_safe_redirect_url(target):
    """Validate that redirect target is a safe, relative URL."""
    if not target:
        return False
    parsed = urlparse(target)
    # Only allow relative URLs (no scheme, no netloc)
    return not parsed.scheme and not parsed.netloc


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10/minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_approved:
                flash('Your account is pending admin approval.', 'warning')
                return render_template('auth/login.html')

            # Check if MFA is enabled
            if user.mfa_enabled:
                session['mfa_user_id'] = user.id
                session['mfa_remember'] = bool(request.form.get('remember'))
                session['mfa_next'] = request.args.get('next')
                return redirect(url_for('auth.mfa_verify'))

            login_user(user, remember=request.form.get('remember'))
            next_page = request.args.get('next')
            if not _is_safe_redirect_url(next_page):
                next_page = None
            return redirect(next_page or url_for('main.dashboard'))
        flash('Invalid username or password.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/mfa-verify', methods=['GET', 'POST'])
def mfa_verify():
    user_id = session.get('mfa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = db.session.get(User, user_id)
    if not user:
        session.pop('mfa_user_id', None)
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        if user.verify_mfa_token(token):
            remember = session.pop('mfa_remember', False)
            next_page = session.pop('mfa_next', None)
            session.pop('mfa_user_id', None)
            login_user(user, remember=remember)
            if not _is_safe_redirect_url(next_page):
                next_page = None
            return redirect(next_page or url_for('main.dashboard'))
        flash('Invalid verification code. Please try again.', 'error')

    return render_template('auth/mfa_verify.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        display_name = request.form.get('display_name', '').strip()

        if not username or not password:
            flash('Username and password are required.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        elif len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
        else:
            user = User(
                username=username,
                display_name=display_name or username,
                role='user',
                is_approved=False,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Account created. An admin must approve your account before you can log in.', 'info')
            return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
