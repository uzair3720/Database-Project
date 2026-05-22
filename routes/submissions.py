"""
routes/submissions.py
Student submits a file; instructor grades it. The grading flow is the
project's showcase transaction (BEGIN ... SET LOCAL ... UPDATE ... COMMIT).
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort

import db as db_module
from auth_helpers import login_required, role_required
from routes.assignments import _allowed_file, _save_upload

submissions_bp = Blueprint("submissions", __name__)


@submissions_bp.route("/submit/<int:assignment_id>", methods=["POST"])
@role_required("student")
def submit(assignment_id):
    """
    Student uploads a file for one assignment. We:
      1. confirm the assignment exists and grab its course_id,
      2. confirm the student is enrolled (the trigger checks again at
         the database level -- belt and braces),
      3. save the file under uploads/submissions/,
      4. INSERT or UPDATE the submissions row.
    """
    user_id = session["user_id"]
    upload  = request.files.get("file")

    if upload is None or not upload.filename:
        flash("Please pick a file to upload.", "danger")
        return redirect(url_for("assignments.detail", assignment_id=assignment_id))

    if not _allowed_file(upload.filename):
        flash("File type not allowed.", "danger")
        return redirect(url_for("assignments.detail", assignment_id=assignment_id))

    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()

        # Find the course this assignment belongs to.
        cur.execute(
            "SELECT course_id FROM assignments WHERE assignment_id = %s",
            (assignment_id,),
        )
        row = cur.fetchone()
        if row is None:
            abort(404)
        course_id = row["course_id"]

        # Application-level enrolment check. The BEFORE INSERT trigger
        # also catches this, but checking here lets us give a nice
        # flash message instead of a 500.
        cur.execute(
            "SELECT 1 FROM enrollments WHERE student_id = %s AND course_id = %s",
            (user_id, course_id),
        )
        if cur.fetchone() is None:
            flash("You are not enrolled in this course.", "danger")
            return redirect(url_for("assignments.detail", assignment_id=assignment_id))

        # Save the file to disk first; if the DB write fails we will
        # leave a stray file on disk, which is acceptable for an
        # academic project (and we log it for cleanup).
        rel_path = _save_upload(upload, "submissions")

        # We allow re-submission by using ON CONFLICT DO UPDATE on the
        # (assignment_id, student_id) unique pair. The grade and
        # feedback columns are NOT touched -- those are the instructor's.
        cur.execute(
            """
            INSERT INTO submissions (assignment_id, student_id, file_path)
            VALUES (%s, %s, %s)
            ON CONFLICT (assignment_id, student_id)
            DO UPDATE SET file_path    = EXCLUDED.file_path,
                          submitted_at = CURRENT_TIMESTAMP,
                          updated_at   = CURRENT_TIMESTAMP
            RETURNING submission_id
            """,
            (assignment_id, user_id, rel_path),
        )
        cur.fetchone()
        conn.commit()
        flash("Submission uploaded.", "success")
    except Exception as exc:
        conn.rollback()
        flash("Could not submit: " + str(exc).splitlines()[0], "danger")
    finally:
        conn.close()
    return redirect(url_for("assignments.detail", assignment_id=assignment_id))


@submissions_bp.route("/<int:submission_id>/grade", methods=["GET", "POST"])
@role_required("instructor")
def grade(submission_id):
    """
    Instructor grades a single submission. The POST branch is the
    show-piece transaction:

        BEGIN;
        SET LOCAL app.current_user_id = <grader>;
        UPDATE submissions SET grade=..., feedback=..., graded_at=NOW();
        COMMIT;

    The SET LOCAL value is read by the trg_log_grade_changes trigger,
    so the audit log captures who did the grading. If anything fails
    after BEGIN, the rollback throws the SET LOCAL away too -- exactly
    why we use SET LOCAL rather than SET.
    """
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        # We need the submission row + assignment max_marks + ownership
        # of the underlying course.
        cur.execute(
            """
            SELECT s.submission_id, s.assignment_id, s.student_id,
                   s.file_path, s.grade, s.feedback,
                   a.title AS assignment_title, a.max_marks, a.course_id,
                   c.instructor_id, u.name AS student_name
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            JOIN courses     c ON c.course_id    = a.course_id
            JOIN users       u ON u.user_id      = s.student_id
            WHERE s.submission_id = %s
            """,
            (submission_id,),
        )
        sub = cur.fetchone()
        if sub is None:
            abort(404)
        if sub["instructor_id"] != session["user_id"]:
            abort(403)

        if request.method == "GET":
            return render_template("submissions/grade.html", sub=sub)

        # POST -- parse and validate the form.
        grade_str = request.form.get("grade", "").strip()
        feedback  = request.form.get("feedback", "").strip()
        try:
            grade_int = int(grade_str)
        except ValueError:
            flash("Grade must be an integer.", "danger")
            return redirect(url_for("submissions.grade", submission_id=submission_id))

        if grade_int < 0 or grade_int > 100:
            flash("Grade must be between 0 and 100 (DB constraint).", "danger")
            return redirect(url_for("submissions.grade", submission_id=submission_id))
        if grade_int > sub["max_marks"]:
            flash("Grade cannot exceed the assignment's max marks (" + str(sub["max_marks"]) + ").", "danger")
            return redirect(url_for("submissions.grade", submission_id=submission_id))

        # ----- Transaction starts here -----
        # psycopg2 is implicitly inside a transaction already (no
        # autocommit). We make that explicit with a savepoint-like
        # pattern: SET LOCAL inside the same transaction, UPDATE,
        # then COMMIT. Any exception triggers rollback in the except.
        try:
            cur.execute(
                "SET LOCAL app.current_user_id = %s",
                (str(session["user_id"]),),
            )
            cur.execute(
                """
                UPDATE submissions
                SET grade     = %s,
                    feedback  = %s,
                    graded_at = CURRENT_TIMESTAMP
                WHERE submission_id = %s
                """,
                (grade_int, feedback, submission_id),
            )
            conn.commit()
        except Exception as inner:
            conn.rollback()
            flash("Grading failed: " + str(inner).splitlines()[0], "danger")
            return redirect(url_for("submissions.grade", submission_id=submission_id))

        flash("Grade saved.", "success")
        return redirect(url_for("assignments.detail", assignment_id=sub["assignment_id"]))
    finally:
        conn.close()
