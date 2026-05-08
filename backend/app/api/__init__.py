"""API router registry for Growth OS.

Imports all sub-routers so they can be included by the main application.
"""

from backend.app.api import loops, goals, assets, insights, reviews, agents, dashboard

__all__ = ["loops", "goals", "assets", "insights", "reviews", "agents", "dashboard"]
