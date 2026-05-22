"""
routes/calendar.py
Read-only calendar view. Events are pulled from assignments.due_date for
every course the user belongs to (instructor: courses they own; student:
courses they're enrolled in).
"""

from datetime import datetime, date

from flask import Blueprint, render_template, session, request

import db as db_module
from auth_helpers import login_required

calendar_bp = Blueprint("calendar", __name__)


@calendar_bp.route("/")
@login_required
def index():
    user_id = session["user_id"]
    role    = session["role"]

    # ?year=YYYY&month=MM controls which month we render. Default = today.
    today = date.today()
    try:
        year  = int(request.args.get("year",  today.year))
        month = int(request.args.get("month", today.month))
    except ValueError:
        year, month = today.year, today.month
    if month < 1 or month > 12:
        year, month = today.year, today.month

    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        if role == "instructor":
            cur.execute(
                """
                SELECT a.assignment_id, a.title, a.due_date,
                       c.course_id, c.course_name, c.course_code, c.join_code
                FROM assignments a
                JOIN courses c ON c.course_id = a.course_id
                WHERE c.instructor_id = %s AND a.due_date IS NOT NULL
                ORDER BY a.due_date
                """,
                (user_id,),
            )
        else:
            cur.execute(
                """
                SELECT a.assignment_id, a.title, a.due_date,
                       c.course_id, c.course_name, c.course_code, c.join_code
                FROM assignments a
                JOIN courses c     ON c.course_id   = a.course_id
                JOIN enrollments e ON e.course_id   = c.course_id
                WHERE e.student_id = %s AND a.due_date IS NOT NULL
                ORDER BY a.due_date
                """,
                (user_id,),
            )
        events = cur.fetchall()
    finally:
        conn.close()

    # Group events by date string for the template.
    by_day = {}
    upcoming = []
    now = datetime.now()
    for ev in events:
        key = ev["due_date"].date().isoformat()
        by_day.setdefault(key, []).append(ev)
        if ev["due_date"] >= now:
            upcoming.append(ev)
    upcoming = sorted(upcoming, key=lambda e: e["due_date"])[:10]

    # First-weekday of the month, Mon=0..Sun=6 — used to offset the grid.
    first_dow = date(year, month, 1).weekday()

    return render_template(
        "calendar/index.html",
        year=year, month=month,
        by_day=by_day,
        upcoming=upcoming,
        today=today,
        first_dow=first_dow,
    )
