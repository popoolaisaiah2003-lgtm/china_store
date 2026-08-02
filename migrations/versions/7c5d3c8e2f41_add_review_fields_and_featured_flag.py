"""add_review_fields_and_featured_flag

Revision ID: 7c5d3c8e2f41
Revises: e59a90072f49
Create Date: 2026-08-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c5d3c8e2f41'
down_revision = 'e59a90072f49'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('customer_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('country', sa.String(length=100), nullable=True, server_default='International'))
        batch_op.add_column(sa.Column('review_text', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('featured', sa.Boolean(), nullable=True, server_default=sa.text('0')))

    op.execute(
        """
        UPDATE reviews
        SET
            customer_name = COALESCE(NULLIF(customer_name, ''), reviewer_name),
            country = COALESCE(NULLIF(country, ''), 'International'),
            review_text = COALESCE(NULLIF(review_text, ''), comment),
            featured = COALESCE(featured, is_approved, 0)
        """
    )


def downgrade():
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_column('featured')
        batch_op.drop_column('review_text')
        batch_op.drop_column('country')
        batch_op.drop_column('customer_name')
