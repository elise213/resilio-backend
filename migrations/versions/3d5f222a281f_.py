"""empty message

Revision ID: 3d5f222a281f
Revises: 6fa37be1f113
Create Date: 2024-03-18 12:22:49.231292

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d5f222a281f'
down_revision = '6fa37be1f113'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('Comment', schema=None) as batch_op:
        batch_op.alter_column('rating_value',
               existing_type=sa.INTEGER(),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('Comment', schema=None) as batch_op:
        batch_op.alter_column('rating_value',
               existing_type=sa.INTEGER(),
               nullable=False)

    # ### end Alembic commands ###