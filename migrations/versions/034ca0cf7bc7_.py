"""empty message

Revision ID: 034ca0cf7bc7
Revises: 6a2f01e83472
Create Date: 2025-03-16 12:33:47.134063

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '034ca0cf7bc7'
down_revision = '6a2f01e83472'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('Resource', schema=None) as batch_op:
        batch_op.drop_column('user_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('Resource', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True))

    # ### end Alembic commands ###
