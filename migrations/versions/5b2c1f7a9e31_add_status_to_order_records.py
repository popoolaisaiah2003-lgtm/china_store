"""add_status_to_order_records

Revision ID: 5b2c1f7a9e31
Revises: 9f6b1d3e4a22
Create Date: 2026-08-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '5b2c1f7a9e31'
down_revision = '9f6b1d3e4a22'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column['name'] for column in inspect(bind).get_columns('order_records')}

    if 'status' not in columns:
        with op.batch_alter_table('order_records', schema=None) as batch_op:
            batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=True, server_default='Pending'))

    op.execute("UPDATE order_records SET status = 'Pending' WHERE status IS NULL OR status = ''")

    with op.batch_alter_table('order_records', schema=None) as batch_op:
        batch_op.alter_column('status', existing_type=sa.String(length=20), nullable=False, server_default='Pending')


def downgrade():
    bind = op.get_bind()
    columns = {column['name'] for column in inspect(bind).get_columns('order_records')}
    if 'status' in columns:
        with op.batch_alter_table('order_records', schema=None) as batch_op:
            batch_op.drop_column('status')
