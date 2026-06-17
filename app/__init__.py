import os
from flask import Flask
from .config import config
from .extensions import db, migrate, login_manager, csrf, limiter


def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Import models so they are registered with SQLAlchemy
    from . import models  # noqa: F401

    # Register blueprints
    from .routes import register_blueprints
    register_blueprints(app)

    _register_activity_log(app)

    return app


def _register_activity_log(app):
    """Record every successful state-changing request as an audit trail entry."""
    from flask import request
    from flask_login import current_user

    @app.after_request
    def _log_activity(response):
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and response.status_code < 400:
            try:
                if getattr(current_user, 'is_authenticated', False):
                    from .models import ActivityLog
                    db.session.add(ActivityLog(
                        user_id=current_user.id,
                        username=current_user.username,
                        method=request.method,
                        endpoint=request.endpoint,
                        path=request.path,
                        status_code=response.status_code,
                    ))
                    db.session.commit()
            except Exception:  # never let logging break a response
                db.session.rollback()
        return response
