"""add_approved_column_to_reviews

Revision ID: c3d9ab4f6d21
Revises: 7c5d3c8e2f41
Create Date: 2026-08-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d9ab4f6d21'
down_revision = '7c5d3c8e2f41'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('approved', sa.Boolean(), nullable=True, server_default=sa.text('0')))

    op.execute(
        """
        UPDATE reviews
        SET approved = COALESCE(approved, is_approved, 0)
        """
    )


def downgrade():
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_column('approved')
