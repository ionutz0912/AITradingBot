"""
HTML View Routes for Dashboard

Serves the dashboard HTML pages.
"""

from flask import Blueprint, render_template

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Render the main dashboard page."""
    return render_template("index.html")


@views_bp.route("/simulations")
def simulations():
    """Render the simulations management page."""
    return render_template("simulations.html")


@views_bp.route("/notifications")
def notifications():
    """Render the notification history page."""
    return render_template("notifications.html")


@views_bp.route("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
