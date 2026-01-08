from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

def utcnow():
    return datetime.utcnow()

# ---------- Team ----------
class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    short_name = db.Column(db.String(50), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

# ---------- User ----------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "admin" | "player"

    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- Player ----------
class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    number = db.Column(db.Integer, nullable=True)
    position = db.Column(db.String(50), nullable=True)
    is_active_global = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

# ---------- Tournament ----------
class Tournament(db.Model):
    __tablename__ = "tournaments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

# ---------- Season ----------
class Season(db.Model):
    __tablename__ = "seasons"

    id = db.Column(db.Integer, primary_key=True)

    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    team = db.relationship("Team")

    year = db.Column(db.Integer, nullable=False)
    term = db.Column(db.String(20), nullable=False)  # winter/spring/summer/fall
    is_active = db.Column(db.Boolean, nullable=False, default=False)

    primary_tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id"), nullable=True)
    primary_tournament = db.relationship("Tournament")

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        db.UniqueConstraint("year", "term", name="uq_season_year_term"),
    )

# ---------- Season roster ----------
class SeasonPlayer(db.Model):
    __tablename__ = "season_players"

    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)

    active = db.Column(db.Boolean, nullable=False, default=True)
    joined_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    left_at = db.Column(db.DateTime, nullable=True)

    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    season = db.relationship("Season")
    player = db.relationship("Player")
    updated_by = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("season_id", "player_id", name="uq_season_player"),
    )

# ---------- Match ----------
class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)

    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    team = db.relationship("Team")

    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id"), nullable=False)

    date_time = db.Column(db.DateTime, nullable=False)
    opponent = db.Column(db.String(120), nullable=False)
    is_home = db.Column(db.Boolean, nullable=False, default=True)
    location = db.Column(db.String(200), nullable=True)

    status = db.Column(db.String(20), nullable=False, default="scheduled")  # scheduled|played|cancelled
    goals_for = db.Column(db.Integer, nullable=False, default=0)
    goals_against = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)

    played_at = db.Column(db.DateTime, nullable=True)
    mvp_opens_at = db.Column(db.DateTime, nullable=True)
    mvp_closes_at = db.Column(db.DateTime, nullable=True)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    season = db.relationship("Season")
    tournament = db.relationship("Tournament")
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    updated_by = db.relationship("User", foreign_keys=[updated_by_user_id])

    def set_played_now(self):
        now = utcnow()
        self.played_at = now
        self.mvp_opens_at = now
        self.mvp_closes_at = now + timedelta(hours=24)

# ---------- Appearances ----------
class Appearance(db.Model):
    __tablename__ = "appearances"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    match = db.relationship("Match")
    player = db.relationship("Player")

    __table_args__ = (
        db.UniqueConstraint("match_id", "player_id", name="uq_appearance_match_player"),
    )

# ---------- Match events ----------
class MatchEvent(db.Model):
    __tablename__ = "match_events"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)

    type = db.Column(db.String(20), nullable=False)  # goal|yellow|red
    minute = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.Text, nullable=True)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    match = db.relationship("Match")
    player = db.relationship("Player")
    created_by = db.relationship("User")

# ---------- MVP votes ----------
class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    voter_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    voted_player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    match = db.relationship("Match")
    voter = db.relationship("User")
    voted_player = db.relationship("Player")

    __table_args__ = (
        db.UniqueConstraint("match_id", "voter_user_id", name="uq_vote_match_voter"),
    )
