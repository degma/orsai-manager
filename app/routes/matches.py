from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Season, Match, RosterMembership, Player, MatchPlayerStat, MVPVote

matches_bp = Blueprint("matches", __name__)
TERMS = ["Winter", "Spring", "Summer", "Fall"]
TERM_ORDER = {term: index for index, term in enumerate(TERMS)}

def get_active_or_latest_season():
    active = Season.query.filter_by(is_active=True).first()
    if active:
        return active
    seasons = Season.query.all()
    if not seasons:
        return None
    seasons.sort(key=lambda season: (season.year, TERM_ORDER.get(season.term, -1)))
    return seasons[-1]

@matches_bp.route("/matches")
@login_required
def list_matches():
    season = get_active_or_latest_season()
    matches = []
    if season:
        matches = (
            Match.query.filter_by(season_id=season.id)
            .order_by(Match.date.desc(), Match.id.desc())
            .all()
        )
    return render_template("matches/list.html", season=season, matches=matches)

@matches_bp.route("/matches/<int:match_id>")
@login_required
def detail(match_id):
    match = db.session.get(Match, match_id)
    if not match:
        abort(404)

    voter_player_id = getattr(current_user, "player_id", None)
    my_stat = None
    current_vote = None
    if voter_player_id:
        my_stat = MatchPlayerStat.query.filter_by(
            match_id=match.id,
            player_id=voter_player_id,
        ).first()
        current_vote = MVPVote.query.filter_by(
            match_id=match.id,
            voter_player_id=voter_player_id,
        ).first()

    mvp_results = []
    if match.status == "played":
        mvp_results = (
            db.session.query(
                Player,
                db.func.count(MVPVote.id).label("vote_count"),
            )
            .join(MVPVote, MVPVote.voted_player_id == Player.id)
            .filter(MVPVote.match_id == match.id)
            .group_by(Player.id)
            .order_by(
                db.func.count(MVPVote.id).desc(),
                Player.last_name.asc(),
                Player.first_name.asc(),
            )
            .all()
        )

    return render_template(
        "matches/detail.html",
        match=match,
        my_stat=my_stat,
        current_vote=current_vote,
        mvp_results=mvp_results,
        voter_player_id=voter_player_id,
    )

@matches_bp.route("/matches/<int:match_id>/vote", methods=["GET", "POST"])
@login_required
def vote(match_id):
    match = db.session.get(Match, match_id)
    if not match:
        abort(404)

    roster_memberships = (
        RosterMembership.query.filter_by(season_id=match.season_id, status="active")
        .join(Player)
        .order_by(Player.last_name.asc(), Player.first_name.asc())
        .all()
    )
    eligible_players = [membership.player for membership in roster_memberships]
    eligible_player_ids = {player.id for player in eligible_players}

    voter_player_id = getattr(current_user, "player_id", None)
    if not voter_player_id:
        flash("Your user is not linked to a player. Contact an admin.", "error")
        return redirect(url_for("matches.list_matches"))

    if request.method == "POST":
        voted_player_id_raw = (request.form.get("voted_player_id") or "").strip()
        try:
            voted_player_id = int(voted_player_id_raw)
        except ValueError:
            voted_player_id = None
        voted_player = db.session.get(Player, voted_player_id) if voted_player_id else None

        if not voted_player or voted_player.id not in eligible_player_ids:
            flash("Selected player is not eligible.", "error")
        elif voted_player.id == voter_player_id:
            flash("You cannot vote for yourself.", "error")
        else:
            vote_record = MVPVote.query.filter_by(
                match_id=match.id,
                voter_player_id=voter_player_id,
            ).first()
            if not vote_record:
                vote_record = MVPVote(
                    match_id=match.id,
                    voter_player_id=voter_player_id,
                    voted_player_id=voted_player.id,
                )
                db.session.add(vote_record)
            else:
                vote_record.voted_player_id = voted_player.id
            db.session.commit()
            flash("Your vote has been recorded.", "success")
            return redirect(url_for("matches.list_matches"))

    current_vote = MVPVote.query.filter_by(
        match_id=match.id,
        voter_player_id=voter_player_id,
    ).first()

    return render_template(
        "matches/vote.html",
        match=match,
        eligible_players=eligible_players,
        current_vote=current_vote,
    )
