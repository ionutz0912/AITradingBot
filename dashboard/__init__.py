"""
AI Trading Bot Web Dashboard

A Flask-based web dashboard for monitoring the trading bot's
performance, positions, market data, and AI signals.
"""

from .app import create_app

__all__ = ["create_app"]
