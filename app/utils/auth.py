from functools import wraps
from flask import abort
from flask_login import login_required, current_user


def role_required(*features):
    """Decorator that checks if the current user can access any of the given features."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if not any(current_user.can_access(feat) for feat in features):
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


auditor_required = role_required('audits')
hardening_required = role_required('hardening')
pentest_required = role_required('pentests')
compliance_required = role_required('compliance')          # write
compliance_view_required = role_required('compliance_view')  # read (viewer+)
