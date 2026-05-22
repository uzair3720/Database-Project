"""
app.py
The Flask entry point. We:
  1. create the Flask app object,
  2. wire up the secret key, upload folder and max upload size,
  3. register every blueprint defined under routes/,
  4. define two thin top-level routes: '/' (index) and '/dashboard',
  5. expose a context processor so the topbar's unread-notification
     badge is correct on every page.

Run with:   flask --app app.py run --debug
"""

import os
from datetime import timedelta

from flask import Flask, session, redirect, url_for, render_template, abort, send_from_directory

import config
import db as db_module
from auth_helpers import login_required

# Blueprints -- imported here, registered below.
from routes.auth          import auth_bp
from routes.courses       import courses_bp
from routes.assignments   import assignments_bp
from routes.submissions   import submissions_bp
from routes.quizzes       import quizzes_bp
from routes.announcements import announcements_bp
from routes.comments      import comments_bp
from routes.notifications import notifications_bp, _unread_count
from routes.calendar      import calendar_bp
from routes.profile       import profile_bp
from routes.search        import search_bp


def _ensure_user_can_see_file(relative_path, user_id, role):
    """
    Authorization for the /uploads/<path> route. A file is served only if:
      - it's an assignment attachment in a course the user belongs to, OR
      - it's a submission file the requesting user owns, OR the requesting
        instructor owns the underlying course.
    Anything not matched -> 403.
    """
    norm = relative_path.replace("\\", "/")
    parts = norm.split("/", 1)
    if len(parts) != 2 or parts[0] not in ("assignments", "submissions"):
        abort(404)

    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        if parts[0] == "assignments":
            cur.execute(
                """
                SELECT a.course_id, c.instructor_id
                FROM assignments a
                JOIN courses c ON c.course_id = a.course_id
                WHERE a.attachment_path = %s
                """,
                (relative_path,),
            )
            row = cur.fetchone()
            if row is None:
                abort(404)
            if role == "instructor":
                if row["instructor_id"] != user_id:
                    abort(403)
            else:
                cur.execute(
                    "SELECT 1 FROM enrollments WHERE student_id = %s AND course_id = %s",
                    (user_id, row["course_id"]),
                )
                if cur.fetchone() is None:
                    abort(403)
        else:  # submissions
            cur.execute(
                """
                SELECT s.student_id, c.instructor_id
                FROM submissions s
                JOIN assignments a ON a.assignment_id = s.assignment_id
                JOIN courses     c ON c.course_id    = a.course_id
                WHERE s.file_path = %s
                """,
                (relative_path,),
            )
            row = cur.fetchone()
            if row is None:
                abort(404)
            if role == "instructor":
                if row["instructor_id"] != user_id:
                    abort(403)
            else:
                if row["student_id"] != user_id:
                    abort(403)
    finally:
        conn.close()


def create_app():
    """Factory that builds and returns the configured Flask app."""
    app = Flask(__name__)
    app.config["SECRET_KEY"]            = config.SECRET_KEY
    app.config["UPLOAD_FOLDER"]         = config.UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"]    = config.MAX_UPLOAD_BYTES
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

    os.makedirs(os.path.join(config.UPLOAD_FOLDER, "assignments"), exist_ok=True)
    os.makedirs(os.path.join(config.UPLOAD_FOLDER, "submissions"), exist_ok=True)

    app.register_blueprint(auth_bp,          url_prefix="/auth")
    app.register_blueprint(courses_bp,       url_prefix="/courses")
    app.register_blueprint(assignments_bp,   url_prefix="/assignments")
    app.register_blueprint(submissions_bp,   url_prefix="/submissions")
    app.register_blueprint(quizzes_bp,       url_prefix="/quizzes")
    app.register_blueprint(announcements_bp, url_prefix="/announcements")
    app.register_blueprint(comments_bp,      url_prefix="/comments")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")
    app.register_blueprint(calendar_bp,      url_prefix="/calendar")
    app.register_blueprint(profile_bp,       url_prefix="/profile")
    app.register_blueprint(search_bp,        url_prefix="/search")

    @app.context_processor
    def inject_unread():
        uid = session.get("user_id")
        if uid is None:
            return {"unread_notifications": 0}
        try:
            return {"unread_notifications": _unread_count(uid)}
        except Exception:
            return {"unread_notifications": 0}

    @app.route("/")
    def index():
        if session.get("user_id") is None:
            return redirect(url_for("auth.login"))
        return redirect(url_for("dashboard"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        user_id = session["user_id"]
        role    = session["role"]
        conn = db_module.get_db_connection()
        try:
            cur = conn.cursor()
            if role == "instructor":
                cur.execute(
                    "SELECT * FROM instructor_dashboard WHERE instructor_id = %s",
                    (user_id,),
                )
                summary = cur.fetchone()

                cur.execute(
                    """
                    SELECT c.course_id, c.course_name, c.course_code, c.join_code,
                           u.name AS instructor_name,
                           (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.course_id) AS enrolled_count,
                           fn_course_average_grade(c.course_id) AS avg_grade
                    FROM courses c
                    JOIN users u ON u.user_id = c.instructor_id
                    WHERE c.instructor_id = %s
                    ORDER BY c.created_at DESC
                    """,
                    (user_id,),
                )
                courses = cur.fetchall()
                return render_template("dashboard.html",
                                       summary=summary, courses=courses)
            else:
                cur.execute(
                    """
                    SELECT c.course_id, c.course_name, c.course_code, c.join_code,
                           u.name AS instructor_name,
                           (SELECT COUNT(*) FROM assignments a WHERE a.course_id = c.course_id) AS total_assignments,
                           (SELECT COUNT(*) FROM submissions s
                              JOIN assignments a ON a.assignment_id = s.assignment_id
                              WHERE a.course_id = c.course_id AND s.student_id = %s AND s.grade IS NOT NULL) AS done_assignments,
                           (SELECT COUNT(*) FROM assignments a
                              WHERE a.course_id = c.course_id
                                AND a.due_date IS NOT NULL
                                AND a.due_date > NOW()
                                AND NOT EXISTS (
                                  SELECT 1 FROM submissions s
                                  WHERE s.assignment_id = a.assignment_id AND s.student_id = %s
                                )) AS upcoming_count
                    FROM enrollments e
                    JOIN courses c ON c.course_id = e.course_id
                    JOIN users   u ON u.user_id   = c.instructor_id
                    WHERE e.student_id = %s
                    ORDER BY e.enrolled_at DESC
                    """,
                    (user_id, user_id, user_id),
                )
                rows = cur.fetchall()
                courses = []
                for r in rows:
                    pct = 0
                    if r["total_assignments"]:
                        pct = int(round(100 * r["done_assignments"] / r["total_assignments"]))
                    courses.append({**r,
                                    "progress_pct": pct,
                                    "upcoming_count": r["upcoming_count"]})
                return render_template("dashboard.html", courses=courses)
        finally:
            conn.close()

    @app.route("/uploads/<path:relative_path>")
    @login_required
    def serve_upload(relative_path):
        _ensure_user_can_see_file(relative_path, session["user_id"], session["role"])
        return send_from_directory(config.UPLOAD_FOLDER, relative_path)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
