"""
routes/assignments.py
Create assignments and show the assignment detail page (which doubles
as the student's submission form and the instructor's list of all
submissions for that assignment).
"""

import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.utils import secure_filename

import db as db_module
import config
from auth_helpers import login_required, role_required

assignments_bp = Blueprint("assignments", __name__)


@assignments_bp.route("/mine")
@login_required
def mine():
    """
    Student: every assignment across enrolled courses, with status.
    Instructor: every assignment they created, with submission counts.
    """
    user_id = session["user_id"]
    role    = session["role"]
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        if role == "instructor":
            cur.execute(
                """
                SELECT a.assignment_id, a.title, a.due_date, a.max_marks,
                       c.course_id, c.course_name, c.course_code, c.join_code,
                       (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id = a.assignment_id) AS submitted_count,
                       (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id = a.assignment_id AND s.grade IS NOT NULL) AS graded_count,
                       (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.course_id) AS enrolled_count
                FROM assignments a
                JOIN courses c ON c.course_id = a.course_id
                WHERE c.instructor_id = %s
                ORDER BY a.due_date NULLS LAST, a.created_at DESC
                """,
                (user_id,),
            )
            items = cur.fetchall()
        else:
            cur.execute(
                """
                SELECT a.assignment_id, a.title, a.due_date, a.max_marks,
                       c.course_id, c.course_name, c.course_code, c.join_code,
                       s.submission_id, s.grade, s.submitted_at
                FROM assignments a
                JOIN courses     c ON c.course_id = a.course_id
                JOIN enrollments e ON e.course_id = c.course_id
                LEFT JOIN submissions s ON s.assignment_id = a.assignment_id AND s.student_id = %s
                WHERE e.student_id = %s
                ORDER BY a.due_date NULLS LAST, a.created_at DESC
                """,
                (user_id, user_id),
            )
            items = cur.fetchall()
        return render_template("assignments/mine.html", items=items, role=role)
    finally:
        conn.close()


def _allowed_file(filename):
    """True if the extension is in the safelist from config.py."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in config.ALLOWED_EXTENSIONS


def _save_upload(file_storage, subfolder):
    """
    Save an uploaded file to uploads/<subfolder>/<uuid>_<safe-name>.
    Returns the path relative to UPLOAD_FOLDER (which is what we store
    in the database).
    """
    safe = secure_filename(file_storage.filename)
    if not safe:
        safe = "file"
    # The uuid prefix prevents collisions if two students upload
    # files with the same name.
    unique = uuid.uuid4().hex + "_" + safe
    rel_path = os.path.join(subfolder, unique)
    full_path = os.path.join(config.UPLOAD_FOLDER, rel_path)
    file_storage.save(full_path)
    return rel_path


@assignments_bp.route("/create/<int:course_id>", methods=["GET", "POST"])
@role_required("instructor")
def create(course_id):
    """
    Instructor creates an assignment inside one of THEIR courses.
    Attachment is optional. We validate the course is theirs before
    we even read the form.
    """
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        # Ownership check first -- this is the standard pattern across
        # every instructor write route.
        cur.execute(
            "SELECT course_id FROM courses WHERE course_id = %s AND instructor_id = %s",
            (course_id, session["user_id"]),
        )
        if cur.fetchone() is None:
            abort(403)

        if request.method == "GET":
            return render_template("assignments/create.html", course_id=course_id)

        title       = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date    = request.form.get("due_date", "").strip() or None
        max_marks   = request.form.get("max_marks", "100").strip()

        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("assignments.create", course_id=course_id))

        try:
            max_marks_int = int(max_marks)
            if max_marks_int <= 0:
                raise ValueError("max_marks must be positive")
        except ValueError:
            flash("Max marks must be a positive integer.", "danger")
            return redirect(url_for("assignments.create", course_id=course_id))

        # Optional attachment from the instructor (e.g. PDF brief).
        attachment_path = None
        upload = request.files.get("attachment")
        if upload is not None and upload.filename:
            if not _allowed_file(upload.filename):
                flash("File type not allowed.", "danger")
                return redirect(url_for("assignments.create", course_id=course_id))
            attachment_path = _save_upload(upload, "assignments")

        cur.execute(
            """
            INSERT INTO assignments
                (course_id, title, description, attachment_path, due_date, max_marks)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING assignment_id
            """,
            (course_id, title, description, attachment_path, due_date, max_marks_int),
        )
        new_id = cur.fetchone()["assignment_id"]
        conn.commit()
        flash("Assignment created.", "success")
        return redirect(url_for("assignments.detail", assignment_id=new_id))
    except Exception as exc:
        conn.rollback()
        flash("Could not create assignment: " + str(exc), "danger")
        return redirect(url_for("courses.detail", course_id=course_id))
    finally:
        conn.close()


@assignments_bp.route("/<int:assignment_id>/edit", methods=["GET", "POST"])
@role_required("instructor")
def edit(assignment_id):
    """Instructor edits an assignment they own (via owning the course)."""
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.*, c.instructor_id
            FROM assignments a
            JOIN courses c ON c.course_id = a.course_id
            WHERE a.assignment_id = %s
            """,
            (assignment_id,),
        )
        a = cur.fetchone()
        if a is None:
            abort(404)
        if a["instructor_id"] != session["user_id"]:
            abort(403)

        if request.method == "GET":
            return render_template("assignments/edit.html", a=a)

        title       = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date    = request.form.get("due_date", "").strip() or None
        try:
            max_marks_int = int(request.form.get("max_marks", "100"))
            if max_marks_int <= 0:
                raise ValueError
        except ValueError:
            flash("Max marks must be a positive integer.", "danger")
            return redirect(url_for("assignments.edit", assignment_id=assignment_id))
        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("assignments.edit", assignment_id=assignment_id))

        cur.execute(
            """
            UPDATE assignments
            SET title = %s, description = %s, due_date = %s, max_marks = %s
            WHERE assignment_id = %s
            """,
            (title, description, due_date, max_marks_int, assignment_id),
        )
        conn.commit()
        flash("Assignment updated.", "success")
        return redirect(url_for("assignments.detail", assignment_id=assignment_id))
    except Exception as exc:
        conn.rollback()
        flash("Could not update: " + str(exc), "danger")
        return redirect(url_for("assignments.detail", assignment_id=assignment_id))
    finally:
        conn.close()


@assignments_bp.route("/<int:assignment_id>/delete", methods=["POST"])
@role_required("instructor")
def delete(assignment_id):
    """Instructor deletes one of their own assignments."""
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.course_id, c.instructor_id
            FROM assignments a
            JOIN courses c ON c.course_id = a.course_id
            WHERE a.assignment_id = %s
            """,
            (assignment_id,),
        )
        row = cur.fetchone()
        if row is None:
            abort(404)
        if row["instructor_id"] != session["user_id"]:
            abort(403)
        cur.execute("DELETE FROM assignments WHERE assignment_id = %s", (assignment_id,))
        conn.commit()
        flash("Assignment deleted.", "info")
        return redirect(url_for("courses.detail", course_id=row["course_id"]))
    except Exception as exc:
        conn.rollback()
        flash("Could not delete: " + str(exc), "danger")
        return redirect(url_for("assignments.detail", assignment_id=assignment_id))
    finally:
        conn.close()


@assignments_bp.route("/<int:assignment_id>")
@login_required
def detail(assignment_id):
    """
    Show one assignment. The template renders different blocks for
    students vs instructors:
      - student: brief, due date, submission form, their own submission
      - instructor: brief and a list of every submission (with grade link)
    """
    user_id = session["user_id"]
    role    = session["role"]
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()

        # The assignment plus its course so we know who owns it.
        cur.execute(
            """
            SELECT a.*, c.course_name, c.instructor_id
            FROM assignments a
            JOIN courses c ON c.course_id = a.course_id
            WHERE a.assignment_id = %s
            """,
            (assignment_id,),
        )
        assignment = cur.fetchone()
        if assignment is None:
            abort(404)

        # Authorization:
        #  - instructor must own the course
        #  - student must be enrolled in the course
        if role == "instructor":
            if assignment["instructor_id"] != user_id:
                abort(403)
        else:
            cur.execute(
                "SELECT 1 FROM enrollments WHERE student_id = %s AND course_id = %s",
                (user_id, assignment["course_id"]),
            )
            if cur.fetchone() is None:
                abort(403)

        # Branch the data we fetch by role.
        my_submission = None
        all_submissions = []
        if role == "student":
            cur.execute(
                """
                SELECT submission_id, file_path, submitted_at, grade, feedback, graded_at
                FROM submissions
                WHERE assignment_id = %s AND student_id = %s
                """,
                (assignment_id, user_id),
            )
            my_submission = cur.fetchone()
        else:
            # Instructor view -- all submissions for this assignment with
            # the student's name.
            cur.execute(
                """
                SELECT s.submission_id, s.file_path, s.submitted_at,
                       s.grade, s.feedback, s.graded_at,
                       u.user_id AS student_id, u.name AS student_name
                FROM submissions s
                JOIN users u ON u.user_id = s.student_id
                WHERE s.assignment_id = %s
                ORDER BY s.submitted_at DESC
                """,
                (assignment_id,),
            )
            all_submissions = cur.fetchall()

        return render_template(
            "assignments/detail.html",
            assignment=assignment,
            my_submission=my_submission,
            all_submissions=all_submissions,
            role=role,
        )
    finally:
        conn.close()
