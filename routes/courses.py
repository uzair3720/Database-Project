"""
routes/courses.py
Everything a course needs: create, list, detail, join, remove student.
"""

import secrets
import string

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort

import db as db_module
from auth_helpers import login_required, role_required

courses_bp = Blueprint("courses", __name__)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def _generate_join_code(cur):
    """
    Build a fresh, unique 6-char code from upper-case letters and digits.
    We loop because a collision, while unlikely with 36**6 codes, is
    technically possible. The cursor is passed in so we use the caller's
    open transaction.
    """
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ""
        for _ in range(6):
            code += secrets.choice(alphabet)
        cur.execute("SELECT 1 FROM courses WHERE join_code = %s", (code,))
        if cur.fetchone() is None:
            return code


def _user_can_see_course(conn, course_id, user_id, role):
    """
    True if this user has any business viewing this course:
      - instructor who owns it, OR
      - student enrolled in it.
    """
    cur = conn.cursor()
    if role == "instructor":
        cur.execute(
            "SELECT 1 FROM courses WHERE course_id = %s AND instructor_id = %s",
            (course_id, user_id),
        )
        return cur.fetchone() is not None
    else:
        cur.execute(
            "SELECT 1 FROM enrollments WHERE course_id = %s AND student_id = %s",
            (course_id, user_id),
        )
        return cur.fetchone() is not None


# --------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------
@courses_bp.route("/browse")
@login_required
def browse():
    """
    Public list of every course in the system. Students use this to
    discover courses; the page shows the join code so they can copy it.
    """
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        # We read the enrolment-count view so the page can show the size
        # of each class. ORDER BY name keeps the list stable.
        cur.execute(
            """
            SELECT cec.*, c.join_code
            FROM course_enrollment_counts cec
            JOIN courses c ON c.course_id = cec.course_id
            ORDER BY cec.course_name
            """
        )
        all_courses = cur.fetchall()
        return render_template("courses/browse.html", all_courses=all_courses)
    finally:
        conn.close()


@courses_bp.route("/create", methods=["GET", "POST"])
@role_required("instructor")
def create():
    """
    Instructor-only. GET shows a form; POST creates a course with a
    fresh join code and bounces to its detail page.
    """
    if request.method == "GET":
        return render_template("courses/create.html")

    name        = request.form.get("course_name", "").strip()
    description = request.form.get("course_description", "").strip()
    course_code = (request.form.get("course_code", "").strip() or None)

    if not name:
        flash("Course name is required.", "danger")
        return redirect(url_for("courses.create"))

    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        join_code = _generate_join_code(cur)

        # We insert and RETURN the new course_id in one round-trip so
        # the redirect can target the course's detail page.
        cur.execute(
            """
            INSERT INTO courses (course_name, course_description, join_code, instructor_id, course_code)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING course_id
            """,
            (name, description, join_code, session["user_id"], course_code),
        )
        new_id = cur.fetchone()["course_id"]
        conn.commit()
        flash("Course created. Share the join code: " + join_code, "success")
        return redirect(url_for("courses.detail", course_id=new_id))
    except Exception as exc:
        conn.rollback()
        flash("Could not create course: " + str(exc), "danger")
        return redirect(url_for("courses.create"))
    finally:
        conn.close()


@courses_bp.route("/my")
@login_required
def my_courses():
    """
    The user's courses. Instructors see what they teach; students see
    what they are enrolled in. One template, two queries.
    """
    user_id = session["user_id"]
    role    = session["role"]
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        if role == "instructor":
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
            courses_list = cur.fetchall()
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
                            AND a.due_date IS NOT NULL AND a.due_date > NOW()
                            AND NOT EXISTS (SELECT 1 FROM submissions s
                                            WHERE s.assignment_id = a.assignment_id AND s.student_id = %s)) AS upcoming_count
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                JOIN users   u ON u.user_id   = c.instructor_id
                WHERE e.student_id = %s
                ORDER BY e.enrolled_at DESC
                """,
                (user_id, user_id, user_id),
            )
            rows = cur.fetchall()
            courses_list = []
            for r in rows:
                pct = 0
                if r["total_assignments"]:
                    pct = int(round(100 * r["done_assignments"] / r["total_assignments"]))
                courses_list.append({**r,
                                     "progress_pct": pct,
                                     "upcoming_count": r["upcoming_count"]})
        return render_template("courses/list.html", courses_list=courses_list)
    finally:
        conn.close()


@courses_bp.route("/join", methods=["GET", "POST"])
@role_required("student")
def join():
    """
    Student joins a course by typing the 6-char code. The actual insert
    happens inside the PL/pgSQL function fn_enroll_student so the
    validation (user is a student, code is real, not already enrolled)
    lives next to the data.
    """
    if request.method == "GET":
        return render_template("courses/list.html", show_join_form=True, courses_list=[])

    join_code = request.form.get("join_code", "").strip().upper()
    if not join_code:
        flash("Please enter a join code.", "danger")
        return redirect(url_for("courses.my_courses"))

    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        # Call the stored function. If anything is wrong it raises
        # an exception we catch and surface as a flash message.
        cur.execute("SELECT fn_enroll_student(%s, %s) AS enrollment_id",
                    (session["user_id"], join_code))
        cur.fetchone()
        conn.commit()
        flash("Enrolled in course.", "success")
    except Exception as exc:
        conn.rollback()
        # The exception's message is the human string raised by RAISE
        # EXCEPTION in PL/pgSQL -- already user-friendly.
        flash("Could not join: " + str(exc).splitlines()[0], "danger")
    finally:
        conn.close()
    return redirect(url_for("courses.my_courses"))


@courses_bp.route("/<int:course_id>")
@login_required
def detail(course_id):
    """
    One course's home page -- assignments, quizzes, announcements,
    students. Access is gated by _user_can_see_course so a student
    can't peek at a course they haven't joined.
    """
    user_id = session["user_id"]
    role    = session["role"]
    conn = db_module.get_db_connection()
    try:
        if not _user_can_see_course(conn, course_id, user_id, role):
            abort(403)

        cur = conn.cursor()

        # Course header info (with instructor name).
        cur.execute(
            """
            SELECT c.*, u.name AS instructor_name
            FROM courses c
            JOIN users   u ON u.user_id = c.instructor_id
            WHERE c.course_id = %s
            """,
            (course_id,),
        )
        course = cur.fetchone()
        if course is None:
            abort(404)

        # Assignments (newest first so the freshest one is at the top).
        cur.execute(
            """
            SELECT assignment_id, title, due_date, max_marks
            FROM assignments
            WHERE course_id = %s
            ORDER BY created_at DESC
            """,
            (course_id,),
        )
        assignments_list = cur.fetchall()

        # Quizzes
        cur.execute(
            """
            SELECT quiz_id, title, total_marks, created_at
            FROM quizzes
            WHERE course_id = %s
            ORDER BY created_at DESC
            """,
            (course_id,),
        )
        quizzes_list = cur.fetchall()

        # Announcements (with poster name).
        cur.execute(
            """
            SELECT a.announcement_id, a.title, a.posted_at, u.name AS poster_name
            FROM announcements a
            JOIN users u ON u.user_id = a.instructor_id
            WHERE a.course_id = %s
            ORDER BY a.posted_at DESC
            """,
            (course_id,),
        )
        announcements_list = cur.fetchall()

        # Enrolled students (instructor only -- students see only their own row).
        students_list = []
        if role == "instructor":
            cur.execute(
                """
                SELECT u.user_id, u.name, u.email, e.enrolled_at
                FROM enrollments e
                JOIN users u ON u.user_id = e.student_id
                WHERE e.course_id = %s
                ORDER BY u.name
                """,
                (course_id,),
            )
            students_list = cur.fetchall()

        # Show the student their own quiz scores on the same page.
        my_quiz_scores = {}
        if role == "student":
            cur.execute(
                """
                SELECT quiz_id, score
                FROM quiz_attempts
                WHERE student_id = %s
                  AND quiz_id IN (SELECT quiz_id FROM quizzes WHERE course_id = %s)
                """,
                (user_id, course_id),
            )
            for r in cur.fetchall():
                my_quiz_scores[r["quiz_id"]] = r["score"]

        # Course average grade, from the PL/pgSQL function.
        cur.execute("SELECT fn_course_average_grade(%s) AS avg_grade", (course_id,))
        avg_row = cur.fetchone()
        course_avg = avg_row["avg_grade"]

        return render_template(
            "courses/detail.html",
            course=course,
            assignments_list=assignments_list,
            quizzes_list=quizzes_list,
            announcements_list=announcements_list,
            students_list=students_list,
            my_quiz_scores=my_quiz_scores,
            course_avg=course_avg,
            is_owner=(role == "instructor" and course["instructor_id"] == user_id),
        )
    finally:
        conn.close()


@courses_bp.route("/<int:course_id>/grades")
@login_required
def grades(course_id):
    """
    Student: their own grades on every assignment in this course plus quiz scores.
    Instructor: gradebook matrix (every enrolled student × every assignment).
    """
    user_id = session["user_id"]
    role    = session["role"]
    conn = db_module.get_db_connection()
    try:
        if not _user_can_see_course(conn, course_id, user_id, role):
            abort(403)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.*, u.name AS instructor_name
            FROM courses c JOIN users u ON u.user_id = c.instructor_id
            WHERE c.course_id = %s
            """,
            (course_id,),
        )
        course = cur.fetchone()

        # Assignments & quizzes are always shown across the top / list.
        cur.execute(
            "SELECT assignment_id, title, max_marks FROM assignments "
            "WHERE course_id = %s ORDER BY created_at",
            (course_id,),
        )
        assignments = cur.fetchall()
        cur.execute(
            "SELECT quiz_id, title, total_marks FROM quizzes "
            "WHERE course_id = %s ORDER BY created_at",
            (course_id,),
        )
        quizzes = cur.fetchall()

        if role == "instructor":
            cur.execute(
                """
                SELECT u.user_id AS student_id, u.name AS student_name
                FROM enrollments e
                JOIN users u ON u.user_id = e.student_id
                WHERE e.course_id = %s
                ORDER BY u.name
                """,
                (course_id,),
            )
            students = cur.fetchall()

            # All submission grades for this course in one query.
            cur.execute(
                """
                SELECT s.student_id, s.assignment_id, s.grade
                FROM submissions s
                JOIN assignments a ON a.assignment_id = s.assignment_id
                WHERE a.course_id = %s
                """,
                (course_id,),
            )
            grade_grid = {}
            for r in cur.fetchall():
                grade_grid[(r["student_id"], r["assignment_id"])] = r["grade"]

            # All quiz scores for this course.
            cur.execute(
                """
                SELECT qa.student_id, qa.quiz_id, qa.score
                FROM quiz_attempts qa
                JOIN quizzes q ON q.quiz_id = qa.quiz_id
                WHERE q.course_id = %s
                """,
                (course_id,),
            )
            quiz_grid = {}
            for r in cur.fetchall():
                quiz_grid[(r["student_id"], r["quiz_id"])] = r["score"]

            return render_template(
                "courses/grades.html",
                course=course, assignments=assignments, quizzes=quizzes,
                students=students, grade_grid=grade_grid, quiz_grid=quiz_grid,
                role="instructor",
            )
        else:
            # Student: their own grades from the view.
            cur.execute(
                """
                SELECT assignment_id, assignment_title, grade, max_marks, feedback,
                       submitted_at, graded_at
                FROM student_grades_view
                WHERE student_id = %s AND course_id = %s
                ORDER BY submitted_at DESC
                """,
                (user_id, course_id),
            )
            my_grades = cur.fetchall()

            cur.execute(
                """
                SELECT q.quiz_id, q.title, q.total_marks, qa.score
                FROM quizzes q
                LEFT JOIN quiz_attempts qa
                       ON qa.quiz_id = q.quiz_id AND qa.student_id = %s
                WHERE q.course_id = %s
                ORDER BY q.created_at
                """,
                (user_id, course_id),
            )
            my_quizzes = cur.fetchall()

            return render_template(
                "courses/grades.html",
                course=course, my_grades=my_grades, my_quizzes=my_quizzes,
                role="student",
            )
    finally:
        conn.close()


@courses_bp.route("/<int:course_id>/edit", methods=["GET", "POST"])
@role_required("instructor")
def edit(course_id):
    """Instructor edits their own course's name, code, or description."""
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM courses WHERE course_id = %s AND instructor_id = %s",
            (course_id, session["user_id"]),
        )
        course = cur.fetchone()
        if course is None:
            abort(403)

        if request.method == "GET":
            return render_template("courses/edit.html", course=course)

        name        = request.form.get("course_name", "").strip()
        description = request.form.get("course_description", "").strip()
        course_code = (request.form.get("course_code", "").strip() or None)
        if not name:
            flash("Course name is required.", "danger")
            return redirect(url_for("courses.edit", course_id=course_id))

        cur.execute(
            """
            UPDATE courses
            SET course_name = %s, course_description = %s, course_code = %s
            WHERE course_id = %s
            """,
            (name, description, course_code, course_id),
        )
        conn.commit()
        flash("Course updated.", "success")
        return redirect(url_for("courses.detail", course_id=course_id))
    except Exception as exc:
        conn.rollback()
        flash("Could not update course: " + str(exc), "danger")
        return redirect(url_for("courses.detail", course_id=course_id))
    finally:
        conn.close()


@courses_bp.route("/<int:course_id>/delete", methods=["POST"])
@role_required("instructor")
def delete(course_id):
    """Instructor deletes their own course. FK CASCADE drops everything under it."""
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM courses WHERE course_id = %s AND instructor_id = %s",
            (course_id, session["user_id"]),
        )
        if cur.rowcount == 0:
            abort(403)
        conn.commit()
        flash("Course deleted.", "info")
    except Exception as exc:
        conn.rollback()
        flash("Could not delete course: " + str(exc), "danger")
    finally:
        conn.close()
    return redirect(url_for("courses.my_courses"))


@courses_bp.route("/<int:course_id>/remove_student/<int:student_id>", methods=["POST"])
@role_required("instructor")
def remove_student(course_id, student_id):
    """
    Instructor removes a student from one of THEIR courses. We verify
    ownership first; without that check, any instructor could kick a
    student out of any course.
    """
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        # Verify the requesting user actually owns the course.
        cur.execute(
            "SELECT 1 FROM courses WHERE course_id = %s AND instructor_id = %s",
            (course_id, session["user_id"]),
        )
        if cur.fetchone() is None:
            abort(403)

        cur.execute(
            "DELETE FROM enrollments WHERE course_id = %s AND student_id = %s",
            (course_id, student_id),
        )
        conn.commit()
        flash("Student removed from course.", "info")
    except Exception as exc:
        conn.rollback()
        flash("Could not remove student: " + str(exc), "danger")
    finally:
        conn.close()
    return redirect(url_for("courses.detail", course_id=course_id))
