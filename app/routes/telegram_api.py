from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import Match, MatchPlayerStat, Player
from app.services.telegram_commands import parse_command, CommandError

telegram_api_bp = Blueprint("telegram_api", __name__, url_prefix="/api/telegram")

def _error(message, hint=None, status=400):
    payload = {"ok": False, "error": message}
    if hint:
        payload["hint"] = hint
    return jsonify(payload), status

@telegram_api_bp.route("/admin", methods=["POST"])
def admin_ingest():
    secret = current_app.config.get("TELEGRAM_INGEST_SECRET")
    if not secret:
        return _error("Server not configured for Telegram ingest.", status=500)

    header_secret = request.headers.get("X-TELEGRAM_SECRET")
    if header_secret != secret:
        return _error("Invalid secret.", status=401)

    payload = request.get_json(silent=True) or {}
    telegram_user_id = payload.get("telegram_user_id")
    text = payload.get("text")

    if not telegram_user_id or not text:
        return _error("Missing telegram_user_id or text.", hint="Provide telegram_user_id and text fields.")

    admin_ids_raw = current_app.config.get("TELEGRAM_ADMIN_IDS", "")
    admin_ids = {item.strip() for item in admin_ids_raw.split(",") if item.strip()}
    if admin_ids and str(telegram_user_id) not in admin_ids:
        return _error("User not authorized.", status=403)
    if not admin_ids:
        return _error("No TELEGRAM_ADMIN_IDS configured.", hint="Set TELEGRAM_ADMIN_IDS=123,456.", status=403)

    try:
        command = parse_command(text)
    except CommandError as exc:
        return _error(str(exc), hint="Use /match <id> score <home>-<away> [notes \"...\"] or /match <id> stats <player> goals=0 y=0 r=0 played=1")

    match = db.session.get(Match, command["match_id"])
    if not match:
        return _error("Match not found.", status=404)

    if command["type"] == "score":
        match.our_score = command["home_score"]
        match.their_score = command["away_score"]
        if command["notes"] is not None:
            match.notes = command["notes"]
        db.session.commit()
        return jsonify({
            "ok": True,
            "message": f"Match {match.id} updated.",
            "data": {
                "match_id": match.id,
                "score": f"{match.our_score}-{match.their_score}",
                "notes": match.notes,
            },
        })

    player = _resolve_player(command["player_identifier"])
    if not player:
        return _error("Player not found.", hint="Use full name or last name.")

    stat = MatchPlayerStat.query.filter_by(match_id=match.id, player_id=player.id).first()
    if not stat:
        stat = MatchPlayerStat(match_id=match.id, player_id=player.id)
        db.session.add(stat)

    stat.played = command["played"]
    stat.goals = command["goals"]
    stat.yellow_cards = command["yellow_cards"]
    stat.red_cards = command["red_cards"]
    db.session.commit()

    return jsonify({
        "ok": True,
        "message": f"Stats updated for {player.first_name} {player.last_name}.",
        "data": {
            "match_id": match.id,
            "player_id": player.id,
            "goals": stat.goals,
            "yellow_cards": stat.yellow_cards,
            "red_cards": stat.red_cards,
            "played": stat.played,
        },
    })


def _resolve_player(identifier: str):
    normalized = identifier.strip().lower()
    if not normalized:
        return None

    candidates = Player.query.all()
    exact = []
    for player in candidates:
        full_name = f"{player.first_name} {player.last_name}".strip().lower()
        if normalized == full_name or normalized == player.first_name.lower() or normalized == player.last_name.lower():
            exact.append(player)

    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None

    partial = [
        player
        for player in candidates
        if normalized in f"{player.first_name} {player.last_name}".lower()
    ]
    return partial[0] if len(partial) == 1 else None
