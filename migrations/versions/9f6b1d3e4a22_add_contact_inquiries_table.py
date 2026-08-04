"""add_contact_inquiries_table

Revision ID: 9f6b1d3e4a22
Revises: c3d9ab4f6d21
Create Date: 2026-08-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '9f6b1d3e4a22'
down_revision = 'c3d9ab4f6d21'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if inspect(bind).has_table('contact_inquiries'):
        return

    op.create_table(
        'contact_inquiries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('company', sa.String(length=150), nullable=True),
        sa.Column('subject', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('contact_inquiries')
