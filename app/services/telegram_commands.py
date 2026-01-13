import shlex

class CommandError(ValueError):
    pass

def tokenize(text: str):
    if not text:
        return []
    return shlex.split(text)

def parse_command(text: str):
    tokens = tokenize(text)
    if len(tokens) < 3:
        raise CommandError("Command is too short.")
    if tokens[0] != "/match":
        raise CommandError("Command must start with /match.")

    try:
        match_id = int(tokens[1])
    except ValueError as exc:
        raise CommandError("Match id must be an integer.") from exc

    action = tokens[2]
    if action == "score":
        return _parse_score(match_id, tokens[3:])
    if action == "stats":
        return _parse_stats(match_id, tokens[3:])

    raise CommandError("Unknown action. Use 'score' or 'stats'.")


def _parse_score(match_id: int, tokens):
    if not tokens:
        raise CommandError("Score is required.")

    score_token = tokens[0]
    if "-" not in score_token:
        raise CommandError("Score must be in home-away format, e.g. 2-1.")

    home_raw, away_raw = score_token.split("-", 1)
    try:
        home_score = int(home_raw)
        away_score = int(away_raw)
    except ValueError as exc:
        raise CommandError("Scores must be integers.") from exc

    if home_score < 0 or away_score < 0:
        raise CommandError("Scores must be zero or higher.")

    notes = None
    if len(tokens) > 1:
        if tokens[1] != "notes":
            raise CommandError("Use notes \"...\" to include match notes.")
        if len(tokens) < 3:
            raise CommandError("Notes text is missing.")
        notes = tokens[2]

    return {
        "type": "score",
        "match_id": match_id,
        "home_score": home_score,
        "away_score": away_score,
        "notes": notes,
    }


def _parse_stats(match_id: int, tokens):
    if len(tokens) < 2:
        raise CommandError("Stats command requires a player identifier and fields.")

    player_identifier = tokens[0]
    fields = {}
    for token in tokens[1:]:
        if "=" not in token:
            raise CommandError("Stats fields must use key=value format.")
        key, value = token.split("=", 1)
        fields[key] = value

    required = ["goals", "y", "r", "played"]
    missing = [key for key in required if key not in fields]
    if missing:
        raise CommandError(f"Missing fields: {', '.join(missing)}.")

    try:
        goals = int(fields["goals"])
        yellow_cards = int(fields["y"])
        red_cards = int(fields["r"])
        played = int(fields["played"])
    except ValueError as exc:
        raise CommandError("Stats values must be integers.") from exc

    if played not in (0, 1):
        raise CommandError("Played must be 0 or 1.")
    if goals < 0 or yellow_cards < 0 or red_cards < 0:
        raise CommandError("Stats values must be zero or higher.")

    return {
        "type": "stats",
        "match_id": match_id,
        "player_identifier": player_identifier,
        "goals": goals,
        "yellow_cards": yellow_cards,
        "red_cards": red_cards,
        "played": bool(played),
    }
