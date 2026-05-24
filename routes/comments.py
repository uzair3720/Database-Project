"""
routes/comments.py
Two endpoints -- one to comment on a submission, one to comment on an
announcement. The comments table is polymorphic, so each endpoint sets
exactly one of submission_id / announcement_id and leaves the other
NULL. The CHECK constraint in the schema makes that contract physical.
"""

from flask import Blueprint, request, redirect, url_for, session, flash, abort

import db as db_module
from auth_helpers import login_required

comments_bp = Blueprint("comments", __name__)


@comments_bp.route("/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete(comment_id):
    """Delete one of your own comments and bounce back to its parent page."""
    user_id = session["user_id"]
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, submission_id, announcement_id FROM comments WHERE comment_id = %s",
            (comment_id,),
        )
        row = cur.fetchone()
        if row is None:
            abort(404)
        if row["user_id"] != user_id:
            abort(403)

        cur.execute("DELETE FROM comments WHERE comment_id = %s", (comment_id,))
        conn.commit()
        flash("Comment deleted.", "info")
        if row["announcement_id"]:
            return redirect(url_for("announcements.detail", announcement_id=row["announcement_id"]))
        if row["submission_id"]:
            return redirect(url_for("submissions.grade", submission_id=row["submission_id"]))
    except Exception as exc:
        conn.rollback()
        flash("Could not delete: " + str(exc), "danger")
    finally:
        conn.close()
    return redirect(url_for("dashboard"))


@comments_bp.route("/submission/<int:submission_id>", methods=["POST"])
@login_required
def on_submission(submission_id):
    """
    Add a comment to a submission. Allowed posters:
      - the student who owns the submission,
      - the instructor who owns the course that owns the assignment.
    """
    user_id = session["user_id"]
    role    = session["role"]
    content = request.form.get("content", "").strip()
    if not content:
        flash("Comment cannot be empty.", "danger")
        return redirect(request.referrer or url_for("dashboard"))

    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        # Pull the submission's owner and the underlying instructor in
        # one query so we don't double-trip the DB.
        cur.execute(
            """
            SELECT s.student_id, c.instructor_id, s.assignment_id
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            JOIN courses     c ON c.course_id    = a.course_id
            WHERE s.submission_id = %s
            """,
            (submission_id,),
        )
        row = cur.fetchone()
        if row is None:
            abort(404)

        allowed = False
        if role == "student" and row["student_id"] == user_id:
            allowed = True
        if role == "instructor" and row["instructor_id"] == user_id:
            allowed = True
        if not allowed:
            abort(403)

        cur.execute(
            """
            INSERT INTO comments (user_id, submission_id, content)
            VALUES (%s, %s, %s)
            """,
            (user_id, submission_id, content),
        )
        conn.commit()
        flash("Comment posted.", "success")
        return redirect(url_for("submissions.grade", submission_id=submission_id)
                        if role == "instructor"
                        else url_for("assignments.detail", assignment_id=row["assignment_id"]))
    except Exception as exc:
        conn.rollback()
        flash("Could not post comment: " + str(exc), "danger")
        return redirect(request.referrer or url_for("dashboard"))
    finally:
        conn.close()


@comments_bp.route("/announcement/<int:announcement_id>", methods=["POST"])
@login_required
def on_announcement(announcement_id):
    """
    Add a comment to an announcement. Allowed posters: anyone who
    belongs to the announcement's course (owner instructor or any
    enrolled student).
    """
    user_id = session["user_id"]
    role    = session["role"]
    content = request.form.get("content", "").strip()
    if not content:
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for("announcements.detail", announcement_id=announcement_id))

    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT course_id, instructor_id FROM announcements WHERE announcement_id = %s",
            (announcement_id,),
        )
        ann = cur.fetchone()
        if ann is None:
            abort(404)

        allowed = False
        if role == "instructor" and ann["instructor_id"] == user_id:
            allowed = True
        if role == "student":
            cur.execute(
                "SELECT 1 FROM enrollments WHERE student_id = %s AND course_id = %s",
                (user_id, ann["course_id"]),
            )
            if cur.fetchone() is not None:
                allowed = True
        if not allowed:
            abort(403)

        cur.execute(
            """
            INSERT INTO comments (user_id, announcement_id, content)
            VALUES (%s, %s, %s)
            """,
            (user_id, announcement_id, content),
        )
        conn.commit()
        flash("Comment posted.", "success")
    except Exception as exc:
        conn.rollback()
        flash("Could not post comment: " + str(exc), "danger")
    finally:
        conn.close()
    return redirect(url_for("announcements.detail", announcement_id=announcement_id))
