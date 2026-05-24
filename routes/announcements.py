"""
routes/announcements.py
Instructor posts an announcement to their course; anyone in that course
can read it and leave a comment.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort

import db as db_module
from auth_helpers import login_required, role_required

announcements_bp = Blueprint("announcements", __name__)


@announcements_bp.route("/create/<int:course_id>", methods=["GET", "POST"])
@role_required("instructor")
def create(course_id):
    """Instructor creates an announcement in their own course."""
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        # Ownership check.
        cur.execute(
            "SELECT 1 FROM courses WHERE course_id = %s AND instructor_id = %s",
            (course_id, session["user_id"]),
        )
        if cur.fetchone() is None:
            abort(403)

        if request.method == "GET":
            return render_template("announcements/create.html", course_id=course_id)

        title   = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("Title and body are both required.", "danger")
            return redirect(url_for("announcements.create", course_id=course_id))

        cur.execute(
            """
            INSERT INTO announcements (course_id, instructor_id, title, content)
            VALUES (%s, %s, %s, %s)
            RETURNING announcement_id
            """,
            (course_id, session["user_id"], title, content),
        )
        new_id = cur.fetchone()["announcement_id"]
        conn.commit()
        flash("Announcement posted.", "success")
        return redirect(url_for("announcements.detail", announcement_id=new_id))
    except Exception as exc:
        conn.rollback()
        flash("Could not post: " + str(exc), "danger")
        return redirect(url_for("courses.detail", course_id=course_id))
    finally:
        conn.close()


@announcements_bp.route("/<int:announcement_id>/edit", methods=["GET", "POST"])
@role_required("instructor")
def edit(announcement_id):
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM announcements WHERE announcement_id = %s",
            (announcement_id,),
        )
        a = cur.fetchone()
        if a is None:
            abort(404)
        if a["instructor_id"] != session["user_id"]:
            abort(403)

        if request.method == "GET":
            return render_template("announcements/edit.html", a=a)

        title   = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("Title and body are both required.", "danger")
            return redirect(url_for("announcements.edit", announcement_id=announcement_id))

        cur.execute(
            "UPDATE announcements SET title = %s, content = %s WHERE announcement_id = %s",
            (title, content, announcement_id),
        )
        conn.commit()
        flash("Post updated.", "success")
        return redirect(url_for("announcements.detail", announcement_id=announcement_id))
    except Exception as exc:
        conn.rollback()
        flash("Could not update: " + str(exc), "danger")
        return redirect(url_for("announcements.detail", announcement_id=announcement_id))
    finally:
        conn.close()


@announcements_bp.route("/<int:announcement_id>/delete", methods=["POST"])
@role_required("instructor")
def delete(announcement_id):
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT course_id, instructor_id FROM announcements WHERE announcement_id = %s",
            (announcement_id,),
        )
        row = cur.fetchone()
        if row is None:
            abort(404)
        if row["instructor_id"] != session["user_id"]:
            abort(403)
        cur.execute("DELETE FROM announcements WHERE announcement_id = %s", (announcement_id,))
        conn.commit()
        flash("Post deleted.", "info")
        return redirect(url_for("courses.detail", course_id=row["course_id"]))
    except Exception as exc:
        conn.rollback()
        flash("Could not delete: " + str(exc), "danger")
        return redirect(url_for("announcements.detail", announcement_id=announcement_id))
    finally:
        conn.close()


@announcements_bp.route("/<int:announcement_id>")
@login_required
def detail(announcement_id):
    """
    The announcement page with its comment thread. Access: the
    requesting user must belong to the announcement's course (either as
    its instructor or as an enrolled student).
    """
    user_id = session["user_id"]
    role    = session["role"]
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.*, c.course_name, c.instructor_id, u.name AS poster_name
            FROM announcements a
            JOIN courses c ON c.course_id = a.course_id
            JOIN users   u ON u.user_id   = a.instructor_id
            WHERE a.announcement_id = %s
            """,
            (announcement_id,),
        )
        ann = cur.fetchone()
        if ann is None:
            abort(404)

        # Authorization: instructor must own; student must be enrolled.
        if role == "instructor":
            if ann["instructor_id"] != user_id:
                abort(403)
        else:
            cur.execute(
                "SELECT 1 FROM enrollments WHERE student_id = %s AND course_id = %s",
                (user_id, ann["course_id"]),
            )
            if cur.fetchone() is None:
                abort(403)

        # Pull all comments tagged to this announcement, with poster names.
        cur.execute(
            """
            SELECT c.comment_id, c.user_id, c.content, c.posted_at, u.name AS poster_name
            FROM comments c
            JOIN users u ON u.user_id = c.user_id
            WHERE c.announcement_id = %s
            ORDER BY c.posted_at ASC
            """,
            (announcement_id,),
        )
        comments_list = cur.fetchall()
        return render_template(
            "announcements/detail.html",
            ann=ann,
            comments_list=comments_list,
        )
    finally:
        conn.close()
