from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"

def create_app():
    
    flask_app = Flask(__name__, template_folder="templates", static_folder="static")
    flask_app.config.from_object(Config)

    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    login_manager.init_app(flask_app)

    import app.models  # noqa: F401

    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(admin_bp)

    from app.cli import register_cli
    register_cli(flask_app)


    return flask_app
