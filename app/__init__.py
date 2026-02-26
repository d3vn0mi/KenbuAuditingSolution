import os
from flask import Flask
from .config import config
from .extensions import db, migrate, login_manager


def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Import models so they are registered with SQLAlchemy
    from . import models  # noqa: F401

    # Register blueprints
    from .routes import register_blueprints
    register_blueprints(app)

    return app
