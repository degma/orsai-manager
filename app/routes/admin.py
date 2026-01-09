from datetime import date
from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import (
    Tournament,
    Season,
    Player,
    RosterMembership,
    Match,
    MatchPlayerStat,
    MVPVote,
    User,
    utcnow,
)

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
    player_users = {
        user.player_id: user
        for user in User.query.filter(User.player_id.isnot(None)).all()
    }
    return render_template(
        "admin/players.html",
        players=players,
        player_users=player_users,
    )

@admin_bp.route("/players/<int:player_id>/create-user", methods=["POST"])
@login_required
def create_player_user(player_id):
    require_admin()
    player = db.session.get(Player, player_id)
    if not player:
        abort(404)

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect(url_for("admin.players"))
    if User.query.filter_by(username=username).first():
        flash("Username is already taken.", "error")
        return redirect(url_for("admin.players"))
    if User.query.filter_by(player_id=player.id).first():
        flash("This player already has a user.", "error")
        return redirect(url_for("admin.players"))

    user = User(username=username, role="player", is_active=True, player_id=player.id)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash("Player user created.", "success")
    return redirect(url_for("admin.players"))

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

@admin_bp.route("/matches", methods=["GET", "POST"])
@login_required
def matches():
    require_admin()
    seasons = Season.query.order_by(Season.year.desc(), Season.term.asc()).all()
    active_season = Season.query.filter_by(is_active=True).first()

    if request.method == "POST":
        season_id_raw = (request.form.get("season_id") or "").strip()
        date_raw = (request.form.get("date") or "").strip()
        opponent = (request.form.get("opponent") or "").strip()
        location = (request.form.get("location") or "").strip()

        try:
            season_id = int(season_id_raw)
        except ValueError:
            season_id = None
        season = db.session.get(Season, season_id) if season_id else None
        try:
            match_date = date.fromisoformat(date_raw) if date_raw else None
        except ValueError:
            match_date = None

        if not season:
            flash("Season is required.", "error")
        elif not match_date:
            flash("Match date is required.", "error")
        elif not opponent:
            flash("Opponent is required.", "error")
        else:
            db.session.add(
                Match(
                    season_id=season.id,
                    date=match_date,
                    opponent=opponent,
                    location=location or None,
                )
            )
            db.session.commit()
            flash("Match created.", "success")
            return redirect(url_for("admin.matches"))

    matches = (
        Match.query.join(Season)
        .order_by(Match.date.desc(), Match.id.desc())
        .all()
    )
    return render_template(
        "admin/matches.html",
        matches=matches,
        seasons=seasons,
        active_season_id=active_season.id if active_season else None,
    )

@admin_bp.route("/matches/<int:match_id>", methods=["GET", "POST"])
@login_required
def match_detail(match_id):
    require_admin()
    match = db.session.get(Match, match_id)
    if not match:
        abort(404)

    if request.method == "POST":
        form_type = request.form.get("form")
        if form_type == "match":
            date_raw = (request.form.get("date") or "").strip()
            opponent = (request.form.get("opponent") or "").strip()
            location = (request.form.get("location") or "").strip()
            status = (request.form.get("status") or "").strip()
            our_score_raw = (request.form.get("our_score") or "").strip()
            their_score_raw = (request.form.get("their_score") or "").strip()
            notes = (request.form.get("notes") or "").strip()

            try:
                match_date = date.fromisoformat(date_raw) if date_raw else None
            except ValueError:
                match_date = None

            try:
                our_score = int(our_score_raw) if our_score_raw else 0
            except ValueError:
                our_score = None

            try:
                their_score = int(their_score_raw) if their_score_raw else 0
            except ValueError:
                their_score = None

            if not match_date:
                flash("Match date is required.", "error")
            elif not opponent:
                flash("Opponent is required.", "error")
            elif status not in ["scheduled", "played", "cancelled"]:
                flash("Status must be scheduled, played, or cancelled.", "error")
            elif our_score is None or their_score is None:
                flash("Scores must be whole numbers.", "error")
            else:
                match.date = match_date
                match.opponent = opponent
                match.location = location or None
                match.status = status
                match.our_score = our_score
                match.their_score = their_score
                match.notes = notes or None
                db.session.commit()
                flash("Match updated.", "success")
                return redirect(url_for("admin.match_detail", match_id=match.id))

        elif form_type == "stats":
            roster_memberships = (
                RosterMembership.query.filter_by(season_id=match.season_id, status="active")
                .join(Player)
                .order_by(Player.last_name.asc(), Player.first_name.asc())
                .all()
            )
            existing_stats = {
                stat.player_id: stat
                for stat in MatchPlayerStat.query.filter_by(match_id=match.id).all()
            }

            for membership in roster_memberships:
                player_id = membership.player_id
                played = request.form.get(f"played_{player_id}") == "on"
                goals_raw = (request.form.get(f"goals_{player_id}") or "").strip()
                yellow_raw = (request.form.get(f"yellow_{player_id}") or "").strip()

                try:
                    goals = int(goals_raw) if goals_raw else 0
                except ValueError:
                    goals = None

                try:
                    yellow_cards = int(yellow_raw) if yellow_raw else 0
                except ValueError:
                    yellow_cards = None

                if goals is None or yellow_cards is None:
                    flash("Goals and yellow cards must be whole numbers.", "error")
                    return redirect(url_for("admin.match_detail", match_id=match.id))

                stat = existing_stats.get(player_id)
                if not stat:
                    stat = MatchPlayerStat(match_id=match.id, player_id=player_id)
                    db.session.add(stat)
                stat.played = played
                stat.goals = goals
                stat.yellow_cards = yellow_cards

            db.session.commit()
            flash("Match stats updated.", "success")
            return redirect(url_for("admin.match_detail", match_id=match.id))

    roster_memberships = (
        RosterMembership.query.filter_by(season_id=match.season_id, status="active")
        .join(Player)
        .order_by(Player.last_name.asc(), Player.first_name.asc())
        .all()
    )
    stats_by_player = {
        stat.player_id: stat
        for stat in MatchPlayerStat.query.filter_by(match_id=match.id).all()
    }

    return render_template(
        "admin/match_detail.html",
        match=match,
        roster_memberships=roster_memberships,
        stats_by_player=stats_by_player,
    )

@admin_bp.route("/matches/<int:match_id>/mvp")
@login_required
def match_mvp(match_id):
    require_admin()
    match = db.session.get(Match, match_id)
    if not match:
        abort(404)

    votes = (
        db.session.query(
            Player,
            db.func.count(MVPVote.id).label("vote_count"),
        )
        .join(MVPVote, MVPVote.voted_player_id == Player.id)
        .filter(MVPVote.match_id == match.id)
        .group_by(Player.id)
        .order_by(db.func.count(MVPVote.id).desc(), Player.last_name.asc())
        .all()
    )

    max_votes = votes[0].vote_count if votes else 0
    winners = [player for player, count in votes if count == max_votes] if votes else []

    return render_template(
        "admin/match_mvp.html",
        match=match,
        votes=votes,
        winners=winners,
        max_votes=max_votes,
    )
