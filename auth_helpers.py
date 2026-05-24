"""
auth_helpers.py
Two decorators every protected route uses:
  - login_required  : redirect to login if the session has no user_id
  - role_required(r): also enforce session['role'] == r
A decorator is a function that takes a function and returns a new
function. We use functools.wraps so Flask still sees the original
view name (Flask uses that name in url_for()).
"""

from functools import wraps
from flask import session, flash, redirect, url_for


def login_required(view_func):
    """
    Wraps a route so that anonymous users are bounced to /auth/login.
    Usage:
        @bp.route("/something")
        @login_required
        def something():
            ...
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)
    return wrapper


def role_required(required_role):
    """
    Decorator factory -- call it with the required role and it returns
    the actual decorator. So you write:
        @role_required('instructor')
        def create_course(): ...
    If the user is not logged in they go to login; if they are logged
    in but the wrong role they get flashed an error and sent to the
    dashboard.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if session.get("user_id") is None:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login"))
            if session.get("role") != required_role:
                flash("You do not have permission to view that page.", "danger")
                return redirect(url_for("dashboard"))
            return view_func(*args, **kwargs)
        return wrapper
    return decorator
