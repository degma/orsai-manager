from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def require_admin():
    if not current_user.is_authenticated:
        abort(401)
    if getattr(current_user, "role", None) != "admin":
        abort(403)

@admin_bp.route("/")
@login_required
def index():
    require_admin()
    return render_template("admin/index.html")
