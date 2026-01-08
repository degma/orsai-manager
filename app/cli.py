import click
from app import db
from app.models import User, Player

def register_cli(app):
    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("password")
    def create_admin(username, password):
        """Create an initial admin user."""
        existing = User.query.filter_by(username=username).first()
        if existing:
            click.echo("User already exists.")
            return

        # Admin can be a player later; leave player_id null for now
        user = User(username=username, role="admin", is_active=True)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        click.echo("Admin user created.")
