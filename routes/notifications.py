"""
routes/notifications.py
List and mark-as-read for the user's notifications feed. Rows are
written by triggers (see db/migrations.sql).
"""

from flask import Blueprint, render_template, redirect, url_for, session, request

import db as db_module
from auth_helpers import login_required

notifications_bp = Blueprint("notifications", __name__)


def _unread_count(user_id):
    """Used by the context processor so the bell badge is correct everywhere."""
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS n FROM notifications WHERE user_id = %s AND is_read = FALSE",
            (user_id,),
        )
        return cur.fetchone()["n"]
    finally:
        conn.close()


@notifications_bp.route("/")
@login_required
def index():
    """Full list, newest first. Marks everything read once viewed."""
    user_id = session["user_id"]
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT notification_id, kind, message, link, is_read, created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 200
            """,
            (user_id,),
        )
        items = cur.fetchall()

        # Mark all as read on open. Cheap UX — the badge clears immediately
        # next page load.
        cur.execute(
            "UPDATE notifications SET is_read = TRUE WHERE user_id = %s AND is_read = FALSE",
            (user_id,),
        )
        conn.commit()
        return render_template("notifications/index.html", items=items)
    finally:
        conn.close()


@notifications_bp.route("/<int:notification_id>/open")
@login_required
def open_link(notification_id):
    """Click-through: mark this one read, then redirect to its link."""
    user_id = session["user_id"]
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT link FROM notifications WHERE notification_id = %s AND user_id = %s",
            (notification_id, user_id),
        )
        row = cur.fetchone()
        if row is None:
            return redirect(url_for("notifications.index"))
        cur.execute(
            "UPDATE notifications SET is_read = TRUE WHERE notification_id = %s",
            (notification_id,),
        )
        conn.commit()
        return redirect(row["link"] or url_for("notifications.index"))
    finally:
        conn.close()
