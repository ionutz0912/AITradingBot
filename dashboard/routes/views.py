"""
HTML View Routes for Dashboard

Serves the main dashboard HTML page.
"""

from flask import Blueprint, render_template

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Render the main dashboard page."""
    return render_template("index.html")


@views_bp.route("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
