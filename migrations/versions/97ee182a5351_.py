"""empty message

Revision ID: 97ee182a5351
Revises: 9eb45042b6ec
Create Date: 2025-03-13 18:18:20.555173

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '97ee182a5351'
down_revision = '9eb45042b6ec'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('Resource', schema=None) as batch_op:
        batch_op.add_column(sa.Column('updated', sa.DateTime(), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('Resource', schema=None) as batch_op:
        batch_op.drop_column('updated')

    # ### end Alembic commands ###
