"""
routes/quizzes.py
Instructor creates a quiz (just title + total marks). After the offline
quiz happens, the instructor enters each student's score from one
page that lists every enrolled student.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort

import db as db_module
from auth_helpers import login_required, role_required

quizzes_bp = Blueprint("quizzes", __name__)


@quizzes_bp.route("/create/<int:course_id>", methods=["GET", "POST"])
@role_required("instructor")
def create(course_id):
    """Instructor creates a quiz in their course."""
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        # Confirm ownership.
        cur.execute(
            "SELECT 1 FROM courses WHERE course_id = %s AND instructor_id = %s",
            (course_id, session["user_id"]),
        )
        if cur.fetchone() is None:
            abort(403)

        if request.method == "GET":
            return render_template("quizzes/create.html", course_id=course_id)

        title       = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        total_marks = request.form.get("total_marks", "100").strip()

        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("quizzes.create", course_id=course_id))
        try:
            total_marks_int = int(total_marks)
            if total_marks_int <= 0:
                raise ValueError
        except ValueError:
            flash("Total marks must be a positive integer.", "danger")
            return redirect(url_for("quizzes.create", course_id=course_id))

        cur.execute(
            """
            INSERT INTO quizzes (course_id, title, description, total_marks)
            VALUES (%s, %s, %s, %s)
            RETURNING quiz_id
            """,
            (course_id, title, description, total_marks_int),
        )
        cur.fetchone()
        conn.commit()
        flash("Quiz created.", "success")
        return redirect(url_for("courses.detail", course_id=course_id))
    except Exception as exc:
        conn.rollback()
        flash("Could not create quiz: " + str(exc), "danger")
        return redirect(url_for("courses.detail", course_id=course_id))
    finally:
        conn.close()


@quizzes_bp.route("/<int:quiz_id>/edit", methods=["GET", "POST"])
@role_required("instructor")
def edit(quiz_id):
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT q.*, c.instructor_id, c.course_id AS c_course_id
            FROM quizzes q
            JOIN courses c ON c.course_id = q.course_id
            WHERE q.quiz_id = %s
            """,
            (quiz_id,),
        )
        q = cur.fetchone()
        if q is None:
            abort(404)
        if q["instructor_id"] != session["user_id"]:
            abort(403)

        if request.method == "GET":
            return render_template("quizzes/edit.html", q=q)

        title       = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        try:
            total_marks_int = int(request.form.get("total_marks", "100"))
            if total_marks_int <= 0:
                raise ValueError
        except ValueError:
            flash("Total marks must be a positive integer.", "danger")
            return redirect(url_for("quizzes.edit", quiz_id=quiz_id))
        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("quizzes.edit", quiz_id=quiz_id))

        cur.execute(
            """
            UPDATE quizzes
            SET title = %s, description = %s, total_marks = %s
            WHERE quiz_id = %s
            """,
            (title, description, total_marks_int, quiz_id),
        )
        conn.commit()
        flash("Quiz updated.", "success")
        return redirect(url_for("courses.detail", course_id=q["course_id"]))
    except Exception as exc:
        conn.rollback()
        flash("Could not update: " + str(exc), "danger")
        return redirect(url_for("quizzes.edit", quiz_id=quiz_id))
    finally:
        conn.close()


@quizzes_bp.route("/<int:quiz_id>/delete", methods=["POST"])
@role_required("instructor")
def delete(quiz_id):
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT q.course_id, c.instructor_id
            FROM quizzes q
            JOIN courses c ON c.course_id = q.course_id
            WHERE q.quiz_id = %s
            """,
            (quiz_id,),
        )
        row = cur.fetchone()
        if row is None:
            abort(404)
        if row["instructor_id"] != session["user_id"]:
            abort(403)
        cur.execute("DELETE FROM quizzes WHERE quiz_id = %s", (quiz_id,))
        conn.commit()
        flash("Quiz deleted.", "info")
        return redirect(url_for("courses.detail", course_id=row["course_id"]))
    except Exception as exc:
        conn.rollback()
        flash("Could not delete: " + str(exc), "danger")
        return redirect(url_for("dashboard"))
    finally:
        conn.close()


@quizzes_bp.route("/<int:quiz_id>/enter_scores", methods=["GET", "POST"])
@role_required("instructor")
def enter_scores(quiz_id):
    """
    Show every enrolled student with their current quiz score (if any)
    and let the instructor save them in one form submission. We use
    INSERT ... ON CONFLICT DO UPDATE so the same form handles both
    "first time entering this score" and "fixing a typo".
    """
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        # Confirm ownership.
        cur.execute(
            """
            SELECT q.quiz_id, q.title, q.total_marks, q.course_id, c.instructor_id
            FROM quizzes q
            JOIN courses c ON c.course_id = q.course_id
            WHERE q.quiz_id = %s
            """,
            (quiz_id,),
        )
        quiz = cur.fetchone()
        if quiz is None:
            abort(404)
        if quiz["instructor_id"] != session["user_id"]:
            abort(403)

        if request.method == "GET":
            # Pull each enrolled student LEFT JOINed with their existing
            # attempt row (if any). LEFT JOIN so students with no score
            # yet still appear with a blank input.
            cur.execute(
                """
                SELECT u.user_id AS student_id, u.name AS student_name,
                       qa.score
                FROM enrollments e
                JOIN users u ON u.user_id = e.student_id
                LEFT JOIN quiz_attempts qa
                       ON qa.quiz_id = %s AND qa.student_id = u.user_id
                WHERE e.course_id = %s
                ORDER BY u.name
                """,
                (quiz_id, quiz["course_id"]),
            )
            students = cur.fetchall()
            return render_template("quizzes/enter_score.html", quiz=quiz, students=students)

        # POST: iterate the form. Inputs are named "score_<student_id>".
        # Empty value means "no score yet" -- we delete or skip those.
        try:
            for key in request.form.keys():
                if not key.startswith("score_"):
                    continue
                student_id_str = key.split("_", 1)[1]
                student_id = int(student_id_str)
                raw_value = request.form.get(key, "").strip()

                if raw_value == "":
                    # No score entered -- leave the row alone (don't
                    # delete an existing score by accident).
                    continue
                score = int(raw_value)
                if score < 0 or score > quiz["total_marks"]:
                    flash("Score for student " + str(student_id) + " out of range.", "danger")
                    conn.rollback()
                    return redirect(url_for("quizzes.enter_scores", quiz_id=quiz_id))

                # Upsert pattern: insert if missing, update if present.
                cur.execute(
                    """
                    INSERT INTO quiz_attempts (quiz_id, student_id, score)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (quiz_id, student_id)
                    DO UPDATE SET score = EXCLUDED.score,
                                  attempted_at = CURRENT_TIMESTAMP
                    """,
                    (quiz_id, student_id, score),
                )
            conn.commit()
            flash("Scores saved.", "success")
        except ValueError:
            conn.rollback()
            flash("All scores must be integers.", "danger")
        except Exception as exc:
            conn.rollback()
            flash("Could not save scores: " + str(exc), "danger")
        return redirect(url_for("courses.detail", course_id=quiz["course_id"]))
    finally:
        conn.close()
