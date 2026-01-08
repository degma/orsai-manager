from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from app.models import User
from app import db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = User.query.filter_by(username=username, is_active=True).first()
        if not user or not user.check_password(password):
            flash("Invalid username or password", "error")
            return render_template("auth/login.html")

        login_user(user)
        return redirect(url_for("admin.index"))

    return render_template("auth/login.html")

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
