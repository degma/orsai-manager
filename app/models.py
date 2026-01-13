from datetime import datetime
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
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    jersey_number = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

# ---------- Tournament ----------
class Tournament(db.Model):
    __tablename__ = "tournaments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

# ---------- Season ----------
class Season(db.Model):
    __tablename__ = "seasons"

    id = db.Column(db.Integer, primary_key=True)

    year = db.Column(db.Integer, nullable=False)
    term = db.Column(db.String(20), nullable=False)  # winter/spring/summer/fall
    is_active = db.Column(db.Boolean, nullable=False, default=False)

    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id"), nullable=False)
    tournament = db.relationship("Tournament")

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        db.UniqueConstraint("year", "term", "tournament_id", name="uq_season_year_term_tournament"),
    )

# ---------- Season roster ----------
class RosterMembership(db.Model):
    __tablename__ = "roster_memberships"

    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)

    status = db.Column(db.String(20), nullable=False, default="active")
    joined_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    left_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    season = db.relationship("Season")
    player = db.relationship("Player")

# ---------- Match ----------
class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)

    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"), nullable=False)

    date = db.Column(db.Date, nullable=False)
    opponent = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200), nullable=True)

    status = db.Column(db.String(20), nullable=False, default="scheduled")  # scheduled|played|cancelled
    our_score = db.Column(db.Integer, nullable=False, default=0)
    their_score = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    season = db.relationship("Season")

# ---------- Match player stats ----------
class MatchPlayerStat(db.Model):
    __tablename__ = "match_player_stats"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)

    played = db.Column(db.Boolean, nullable=False, default=True)
    goals = db.Column(db.Integer, nullable=False, default=0)
    yellow_cards = db.Column(db.Integer, nullable=False, default=0)
    red_cards = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    match = db.relationship("Match")
    player = db.relationship("Player")

    __table_args__ = (
        db.UniqueConstraint("match_id", "player_id", name="uq_match_player_stats"),
        db.CheckConstraint("red_cards >= 0", name="ck_match_player_stats_red_cards_nonneg"),
    )

# ---------- MVP votes ----------
class MVPVote(db.Model):
    __tablename__ = "mvp_votes"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    voter_player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    voted_player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    match = db.relationship("Match")
    voter_player = db.relationship("Player", foreign_keys=[voter_player_id])
    voted_player = db.relationship("Player", foreign_keys=[voted_player_id])

    __table_args__ = (
        db.UniqueConstraint("match_id", "voter_player_id", name="uq_mvp_vote_match_voter"),
        db.CheckConstraint("voter_player_id != voted_player_id", name="ck_mvp_vote_no_self"),
    )
