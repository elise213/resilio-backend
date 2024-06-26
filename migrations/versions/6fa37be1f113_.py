"""empty message

Revision ID: 6fa37be1f113
Revises: c51be90ce862
Create Date: 2024-03-18 12:15:21.775600

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6fa37be1f113'
down_revision = 'c51be90ce862'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('Comment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rating_value', sa.Integer(), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('Comment', schema=None) as batch_op:
        batch_op.drop_column('rating_value')

    # ### end Alembic commands ###
