"""
routes/search.py
Global search across the user's courses, assignments, and announcements.
We only return rows the user is allowed to see (instructor-owned or
student-enrolled). Title-prefix match using ILIKE.
"""

from flask import Blueprint, render_template, request, session

import db as db_module
from auth_helpers import login_required

search_bp = Blueprint("search", __name__)


@search_bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    user_id = session["user_id"]
    role    = session["role"]
    results = {"courses": [], "assignments": [], "announcements": []}

    if not q:
        return render_template("search/index.html", q="", results=results)

    like = "%" + q + "%"
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()

        # Courses
        if role == "instructor":
            cur.execute(
                """
                SELECT course_id, course_name, course_code, join_code
                FROM courses
                WHERE instructor_id = %s
                  AND (course_name ILIKE %s OR course_code ILIKE %s OR join_code ILIKE %s)
                ORDER BY course_name LIMIT 25
                """,
                (user_id, like, like, like),
            )
        else:
            cur.execute(
                """
                SELECT c.course_id, c.course_name, c.course_code, c.join_code
                FROM courses c
                JOIN enrollments e ON e.course_id = c.course_id
                WHERE e.student_id = %s
                  AND (c.course_name ILIKE %s OR c.course_code ILIKE %s OR c.join_code ILIKE %s)
                ORDER BY c.course_name LIMIT 25
                """,
                (user_id, like, like, like),
            )
        results["courses"] = cur.fetchall()

        # Assignments
        if role == "instructor":
            cur.execute(
                """
                SELECT a.assignment_id, a.title, a.due_date, c.course_id, c.course_name
                FROM assignments a
                JOIN courses c ON c.course_id = a.course_id
                WHERE c.instructor_id = %s AND a.title ILIKE %s
                ORDER BY a.created_at DESC LIMIT 25
                """,
                (user_id, like),
            )
        else:
            cur.execute(
                """
                SELECT a.assignment_id, a.title, a.due_date, c.course_id, c.course_name
                FROM assignments a
                JOIN courses c     ON c.course_id = a.course_id
                JOIN enrollments e ON e.course_id = c.course_id
                WHERE e.student_id = %s AND a.title ILIKE %s
                ORDER BY a.created_at DESC LIMIT 25
                """,
                (user_id, like),
            )
        results["assignments"] = cur.fetchall()

        # Announcements
        if role == "instructor":
            cur.execute(
                """
                SELECT a.announcement_id, a.title, a.posted_at, c.course_id, c.course_name
                FROM announcements a
                JOIN courses c ON c.course_id = a.course_id
                WHERE c.instructor_id = %s AND (a.title ILIKE %s OR a.content ILIKE %s)
                ORDER BY a.posted_at DESC LIMIT 25
                """,
                (user_id, like, like),
            )
        else:
            cur.execute(
                """
                SELECT a.announcement_id, a.title, a.posted_at, c.course_id, c.course_name
                FROM announcements a
                JOIN courses c     ON c.course_id = a.course_id
                JOIN enrollments e ON e.course_id = c.course_id
                WHERE e.student_id = %s AND (a.title ILIKE %s OR a.content ILIKE %s)
                ORDER BY a.posted_at DESC LIMIT 25
                """,
                (user_id, like, like),
            )
        results["announcements"] = cur.fetchall()
    finally:
        conn.close()

    return render_template("search/index.html", q=q, results=results)
