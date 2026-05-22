"""
routes/profile.py
Profile page: view + edit name, change password, role-aware stats.
"""

import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

import db as db_module
from auth_helpers import login_required

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/")
@login_required
def index():
    user_id = session["user_id"]
    role    = session["role"]
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, name, email, role, created_at FROM users WHERE user_id = %s",
            (user_id,),
        )
        user = cur.fetchone()

        stats = {}
        if role == "instructor":
            # We already have the instructor_dashboard view for these counts.
            cur.execute(
                "SELECT total_courses, total_students, total_assignments "
                "FROM instructor_dashboard WHERE instructor_id = %s",
                (user_id,),
            )
            row = cur.fetchone() or {}
            stats = {
                "courses":     row.get("total_courses", 0)     or 0,
                "students":    row.get("total_students", 0)    or 0,
                "assignments": row.get("total_assignments", 0) or 0,
            }
        else:
            cur.execute("SELECT COUNT(*) AS n FROM enrollments WHERE student_id = %s", (user_id,))
            courses_n = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM submissions WHERE student_id = %s", (user_id,))
            subs_n = cur.fetchone()["n"]
            cur.execute(
                "SELECT AVG(grade)::NUMERIC(6,2) AS avg_grade FROM submissions "
                "WHERE student_id = %s AND grade IS NOT NULL",
                (user_id,),
            )
            avg = cur.fetchone()["avg_grade"]
            stats = {"courses": courses_n, "submissions": subs_n, "avg_grade": avg}

        return render_template("profile/index.html", user=user, stats=stats)
    finally:
        conn.close()


@profile_bp.route("/edit", methods=["POST"])
@login_required
def edit():
    new_name = request.form.get("name", "").strip()
    if not new_name:
        flash("Name cannot be empty.", "danger")
        return redirect(url_for("profile.index"))
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET name = %s WHERE user_id = %s",
                    (new_name, session["user_id"]))
        conn.commit()
        session["name"] = new_name
        flash("Profile updated.", "success")
    except Exception as exc:
        conn.rollback()
        flash("Could not update: " + str(exc), "danger")
    finally:
        conn.close()
    return redirect(url_for("profile.index"))


@profile_bp.route("/password", methods=["POST"])
@login_required
def change_password():
    current = request.form.get("current", "")
    new_pw  = request.form.get("new", "")
    confirm = request.form.get("confirm", "")

    if not current or not new_pw:
        flash("Fill every field.", "danger")
        return redirect(url_for("profile.index"))
    if new_pw != confirm:
        flash("New passwords don't match.", "danger")
        return redirect(url_for("profile.index"))
    if len(new_pw) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return redirect(url_for("profile.index"))

    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE user_id = %s",
                    (session["user_id"],))
        row = cur.fetchone()
        if not bcrypt.checkpw(current.encode("utf-8"), row["password_hash"].encode("utf-8")):
            flash("Current password is wrong.", "danger")
            return redirect(url_for("profile.index"))

        new_hash = bcrypt.hashpw(new_pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur.execute("UPDATE users SET password_hash = %s WHERE user_id = %s",
                    (new_hash, session["user_id"]))
        conn.commit()
        flash("Password changed.", "success")
    except Exception as exc:
        conn.rollback()
        flash("Could not change password: " + str(exc), "danger")
    finally:
        conn.close()
    return redirect(url_for("profile.index"))
