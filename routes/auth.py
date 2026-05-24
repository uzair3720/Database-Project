"""
routes/auth.py
Signup, login, logout, forgot-password, reset-password.

Passwords are bcrypt-hashed. Forgot-password creates a single-use token in
the password_reset_tokens table; if SMTP env vars are set we email the link,
otherwise we print it to the Flask console (so the flow works without
external services during development / viva).
"""

import os
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

import db as db_module

auth_bp = Blueprint("auth", __name__)


def _send_reset_email(to_email, reset_url):
    """If SMTP_HOST is unset we just print to the Flask console."""
    host = os.environ.get("SMTP_HOST")
    if not host:
        print("\n=== Password reset link (SMTP not configured) ===")
        print("  to:  " + to_email)
        print("  url: " + reset_url)
        print("=================================================\n")
        return

    port     = int(os.environ.get("SMTP_PORT", "587"))
    user     = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    sender   = os.environ.get("SMTP_FROM", user or "no-reply@lmp.local")

    msg = EmailMessage()
    msg["Subject"] = "Reset your LMP password"
    msg["From"]    = sender
    msg["To"]      = to_email
    msg.set_content(
        "Click the link below to reset your LMP password (valid for 1 hour):\n\n"
        + reset_url + "\n\nIf you did not request this, ignore the email."
    )
    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("auth/signup.html")

    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role     = request.form.get("role", "")

    if not name or not email or not password or role not in ("student", "instructor"):
        flash("Please fill every field and pick a valid role.", "danger")
        return redirect(url_for("auth.signup"))
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return redirect(url_for("auth.signup"))

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
        if cur.fetchone() is not None:
            flash("That email is already registered. Try logging in.", "danger")
            return redirect(url_for("auth.signup"))

        cur.execute(
            """
            INSERT INTO users (name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id
            """,
            (name, email, pw_hash.decode("utf-8"), role),
        )
        new_user_id = cur.fetchone()["user_id"]
        conn.commit()

        session.clear()
        session["user_id"] = new_user_id
        session["name"]    = name
        session["role"]    = role
        flash("Welcome to LMP, " + name + "!", "success")
        return redirect(url_for("dashboard"))
    except Exception as exc:
        conn.rollback()
        flash("Could not create account: " + str(exc), "danger")
        return redirect(url_for("auth.signup"))
    finally:
        conn.close()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html")

    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    remember = request.form.get("remember") == "on"

    if not email or not password:
        flash("Please enter your email and password.", "danger")
        return redirect(url_for("auth.login"))

    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, name, password_hash, role FROM users WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
        if row is None or not bcrypt.checkpw(password.encode("utf-8"),
                                             row["password_hash"].encode("utf-8")):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("auth.login"))

        session.clear()
        session["user_id"] = row["user_id"]
        session["name"]    = row["name"]
        session["role"]    = row["role"]
        # Permanent session honours app.config["PERMANENT_SESSION_LIFETIME"].
        session.permanent  = remember
        flash("Logged in as " + row["name"], "success")
        return redirect(url_for("dashboard"))
    finally:
        conn.close()


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "GET":
        return render_template("auth/forgot.html")

    email = request.form.get("email", "").strip().lower()
    if not email:
        flash("Please enter your email.", "danger")
        return redirect(url_for("auth.forgot"))

    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        if row is not None:
            token = secrets.token_urlsafe(32)
            cur.execute(
                """
                INSERT INTO password_reset_tokens (token, user_id, expires_at)
                VALUES (%s, %s, %s)
                """,
                (token, row["user_id"], datetime.utcnow() + timedelta(hours=1)),
            )
            conn.commit()
            reset_url = url_for("auth.reset", token=token, _external=True)
            try:
                _send_reset_email(email, reset_url)
            except Exception as exc:
                print("SMTP send failed:", exc)
        # Same message regardless so we don't leak whether the email exists.
        flash("If that email is registered, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    finally:
        conn.close()


@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    conn = db_module.get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, expires_at, used_at FROM password_reset_tokens WHERE token = %s",
            (token,),
        )
        row = cur.fetchone()
        if row is None or row["used_at"] is not None or row["expires_at"] < datetime.utcnow():
            flash("This reset link is invalid or expired.", "danger")
            return redirect(url_for("auth.forgot"))

        if request.method == "GET":
            return render_template("auth/reset.html", token=token)

        new_pw  = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if len(new_pw) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("auth.reset", token=token))
        if new_pw != confirm:
            flash("Passwords don't match.", "danger")
            return redirect(url_for("auth.reset", token=token))

        new_hash = bcrypt.hashpw(new_pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur.execute("UPDATE users SET password_hash = %s WHERE user_id = %s",
                    (new_hash, row["user_id"]))
        cur.execute("UPDATE password_reset_tokens SET used_at = %s WHERE token = %s",
                    (datetime.utcnow(), token))
        conn.commit()
        flash("Password updated — you can now sign in.", "success")
        return redirect(url_for("auth.login"))
    finally:
        conn.close()


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
