from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Tournament, Season, Player, RosterMembership, utcnow

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
TERMS = ["Winter", "Spring", "Summer", "Fall"]

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

@admin_bp.route("/tournaments", methods=["GET", "POST"])
@login_required
def tournaments():
    require_admin()
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Tournament name is required.", "error")
        elif Tournament.query.filter_by(name=name).first():
            flash("Tournament name must be unique.", "error")
        else:
            db.session.add(Tournament(name=name))
            db.session.commit()
            flash("Tournament created.", "success")
            return redirect(url_for("admin.tournaments"))

    tournaments = Tournament.query.order_by(Tournament.name.asc()).all()
    return render_template("admin/tournaments.html", tournaments=tournaments)

@admin_bp.route("/tournaments/<int:tournament_id>/delete", methods=["POST"])
@login_required
def delete_tournament(tournament_id):
    require_admin()
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        abort(404)
    if Season.query.filter_by(tournament_id=tournament.id).first():
        flash("Tournament has seasons and cannot be deleted.", "error")
        return redirect(url_for("admin.tournaments"))

    db.session.delete(tournament)
    db.session.commit()
    flash("Tournament deleted.", "success")
    return redirect(url_for("admin.tournaments"))

@admin_bp.route("/seasons", methods=["GET", "POST"])
@login_required
def seasons():
    require_admin()
    tournaments = Tournament.query.order_by(Tournament.name.asc()).all()

    if request.method == "POST":
        year_raw = (request.form.get("year") or "").strip()
        term = (request.form.get("term") or "").strip()
        tournament_id = request.form.get("tournament_id")

        try:
            year = int(year_raw)
        except ValueError:
            year = None

        tournament = db.session.get(Tournament, tournament_id) if tournament_id else None

        if not year:
            flash("Season year is required.", "error")
        elif term not in TERMS:
            flash("Season term must be Winter, Spring, Summer, or Fall.", "error")
        elif not tournament:
            flash("Tournament is required.", "error")
        elif Season.query.filter_by(year=year, term=term, tournament_id=tournament.id).first():
            flash("Season already exists for that tournament and term.", "error")
        else:
            db.session.add(Season(year=year, term=term, tournament_id=tournament.id))
            db.session.commit()
            flash("Season created.", "success")
            return redirect(url_for("admin.seasons"))

    seasons = Season.query.order_by(Season.year.desc(), Season.term.asc()).all()
    return render_template(
        "admin/seasons.html",
        seasons=seasons,
        tournaments=tournaments,
        terms=TERMS,
    )

@admin_bp.route("/seasons/<int:season_id>/activate", methods=["POST"])
@login_required
def activate_season(season_id):
    require_admin()
    season = db.session.get(Season, season_id)
    if not season:
        abort(404)

    Season.query.filter_by(is_active=True).update({Season.is_active: False})
    season.is_active = True
    db.session.commit()
    flash("Season activated.", "success")
    return redirect(url_for("admin.seasons"))

@admin_bp.route("/players", methods=["GET", "POST"])
@login_required
def players():
    require_admin()
    if request.method == "POST":
        first_name = (request.form.get("first_name") or "").strip()
        last_name = (request.form.get("last_name") or "").strip()
        jersey_number_raw = (request.form.get("jersey_number") or "").strip()

        jersey_number = None
        if jersey_number_raw:
            try:
                jersey_number = int(jersey_number_raw)
            except ValueError:
                jersey_number = "invalid"

        if not first_name or not last_name:
            flash("First and last name are required.", "error")
        elif jersey_number == "invalid":
            flash("Jersey number must be a whole number.", "error")
        else:
            db.session.add(
                Player(
                    first_name=first_name,
                    last_name=last_name,
                    jersey_number=jersey_number,
                )
            )
            db.session.commit()
            flash("Player created.", "success")
            return redirect(url_for("admin.players"))

    players = Player.query.order_by(Player.last_name.asc(), Player.first_name.asc()).all()
    return render_template("admin/players.html", players=players)

@admin_bp.route("/players/<int:player_id>/deactivate", methods=["POST"])
@login_required
def deactivate_player(player_id):
    require_admin()
    player = db.session.get(Player, player_id)
    if not player:
        abort(404)
    player.is_active = False
    db.session.commit()
    flash("Player deactivated.", "success")
    return redirect(url_for("admin.players"))

@admin_bp.route("/seasons/<int:season_id>/roster", methods=["GET", "POST"])
@login_required
def season_roster(season_id):
    require_admin()
    season = db.session.get(Season, season_id)
    if not season:
        abort(404)

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        player_id = request.form.get("player_id")
        player = db.session.get(Player, player_id) if player_id else None

        if action == "add":
            if not player or not player.is_active:
                flash("Player is required.", "error")
            else:
                active_membership = RosterMembership.query.filter_by(
                    season_id=season.id,
                    player_id=player.id,
                    status="active",
                ).first()
                if active_membership:
                    flash("Player is already active on this roster.", "error")
                else:
                    db.session.add(
                        RosterMembership(
                            season_id=season.id,
                            player_id=player.id,
                        )
                    )
                    db.session.commit()
                    flash("Player added to roster.", "success")
                    return redirect(url_for("admin.season_roster", season_id=season.id))
        elif action == "remove":
            if not player:
                flash("Player is required.", "error")
            else:
                active_membership = RosterMembership.query.filter_by(
                    season_id=season.id,
                    player_id=player.id,
                    status="active",
                ).first()
                if not active_membership:
                    flash("Player is not active on this roster.", "error")
                else:
                    active_membership.status = "inactive"
                    active_membership.left_at = utcnow()
                    db.session.commit()
                    flash("Player removed from roster.", "success")
                    return redirect(url_for("admin.season_roster", season_id=season.id))

    active_memberships = (
        RosterMembership.query.filter_by(season_id=season.id, status="active")
        .join(Player)
        .order_by(Player.last_name.asc(), Player.first_name.asc())
        .all()
    )
    inactive_memberships = (
        RosterMembership.query.filter_by(season_id=season.id, status="inactive")
        .join(Player)
        .order_by(RosterMembership.left_at.desc())
        .all()
    )
    active_player_ids = {membership.player_id for membership in active_memberships}
    available_players = Player.query.filter_by(is_active=True).all()
    available_players = [
        player for player in available_players if player.id not in active_player_ids
    ]
    available_players.sort(key=lambda player: (player.last_name, player.first_name))

    return render_template(
        "admin/roster.html",
        season=season,
        active_memberships=active_memberships,
        inactive_memberships=inactive_memberships,
        available_players=available_players,
    )
