"""Add red_cards to match_player_stats

Revision ID: 4a9b8c7d1b32
Revises: 15d3251655a9
Create Date: 2026-01-09 00:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4a9b8c7d1b32'
down_revision = '15d3251655a9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('match_player_stats', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('red_cards', sa.Integer(), nullable=False, server_default='0')
        )

    # opcional: quitar default a nivel DB después de crear columna
    with op.batch_alter_table('match_player_stats', schema=None) as batch_op:
        batch_op.alter_column('red_cards', server_default=None)


def downgrade():
    with op.batch_alter_table('match_player_stats', schema=None) as batch_op:
        batch_op.drop_column('red_cards')
