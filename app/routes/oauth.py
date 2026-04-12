import secrets
import requests as http_requests
from flask import Blueprint, redirect, url_for, flash, session, current_app, request
from flask_login import login_user, current_user
from ..extensions import db
from ..models.user import User

oauth_bp = Blueprint('oauth', __name__, url_prefix='/oauth')

GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_API_URL = 'https://api.github.com'


@oauth_bp.route('/github')
def github_login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    client_id = current_app.config.get('GITHUB_CLIENT_ID')
    if not client_id:
        flash('GitHub SSO is not configured.', 'error')
        return redirect(url_for('auth.login'))

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    redirect_uri = url_for('oauth.github_callback', _external=True)
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': 'user:email',
        'state': state,
    }
    query = '&'.join(f'{k}={v}' for k, v in params.items())
    return redirect(f'{GITHUB_AUTHORIZE_URL}?{query}')


@oauth_bp.route('/github/callback')
def github_callback():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    client_id = current_app.config.get('GITHUB_CLIENT_ID')
    client_secret = current_app.config.get('GITHUB_CLIENT_SECRET')
    if not client_id or not client_secret:
        flash('GitHub SSO is not configured.', 'error')
        return redirect(url_for('auth.login'))

    # Verify state for CSRF protection
    state = request.args.get('state')
    if not state or state != session.pop('oauth_state', None):
        flash('Authentication failed: invalid state.', 'error')
        return redirect(url_for('auth.login'))

    code = request.args.get('code')
    if not code:
        flash('Authentication failed: no authorization code.', 'error')
        return redirect(url_for('auth.login'))

    # Exchange code for access token
    token_resp = http_requests.post(
        GITHUB_TOKEN_URL,
        json={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
        },
        headers={'Accept': 'application/json'},
        timeout=10,
    )

    if token_resp.status_code != 200:
        flash('GitHub authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    token_data = token_resp.json()
    access_token = token_data.get('access_token')
    if not access_token:
        flash('GitHub authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    # Fetch user profile from GitHub
    user_resp = http_requests.get(
        f'{GITHUB_API_URL}/user',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
        },
        timeout=10,
    )

    if user_resp.status_code != 200:
        flash('Failed to fetch GitHub profile.', 'error')
        return redirect(url_for('auth.login'))

    github_user = user_resp.json()
    github_id = github_user.get('id')
    github_username = github_user.get('login', '')
    display_name = github_user.get('name') or github_username
    avatar_url = github_user.get('avatar_url', '')

    # Look up existing user by github_id
    user = User.query.filter_by(github_id=github_id).first()

    if user:
        # Update profile info from GitHub
        user.display_name = display_name
        user.avatar_url = avatar_url
        db.session.commit()
    else:
        # Check if a local user has the same username
        existing = User.query.filter_by(username=github_username).first()
        if existing:
            # Do NOT auto-link: a matching username does not prove ownership.
            # The user must link their GitHub account from account settings.
            flash('A local account with that username already exists. '
                  'Please log in with your password to link your GitHub account.', 'warning')
            return redirect(url_for('auth.login'))
        else:
            # Create new user (pending approval)
            user = User(
                username=github_username,
                display_name=display_name,
                auth_provider='github',
                github_id=github_id,
                avatar_url=avatar_url,
                role='user',
                is_approved=False,
            )
            db.session.add(user)
            db.session.commit()

    if not user.is_approved:
        flash('Your account is pending admin approval.', 'warning')
        return redirect(url_for('auth.login'))

    login_user(user, remember=True)
    return redirect(url_for('main.dashboard'))
