def register_blueprints(app):
    from .auth import auth_bp
    from .main import main_bp
    from .benchmarks import benchmarks_bp
    from .platforms import platforms_bp
    from .checks import checks_bp
    from .audits import audits_bp
    from .export import export_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(benchmarks_bp)
    app.register_blueprint(platforms_bp)
    app.register_blueprint(checks_bp)
    app.register_blueprint(audits_bp)
    app.register_blueprint(export_bp)
