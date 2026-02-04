"""
Flask Application Factory for AI Trading Bot Dashboard

Creates and configures the Flask application with:
- API routes for data endpoints
- View routes for HTML pages
- CORS support for development
"""

from flask import Flask


def create_app(config: dict = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured Flask application
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    # Default configuration
    app.config.update(
        SECRET_KEY="dev-key-change-in-production",
        JSON_SORT_KEYS=False,
    )

    # Apply custom config if provided
    if config:
        app.config.update(config)

    # Register blueprints
    from .routes.api import api_bp
    from .routes.views import views_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(views_bp)

    return app
