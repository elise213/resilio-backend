"""empty message

Revision ID: 700bc6d75c54
Revises: 05b2198969b5
Create Date: 2025-03-26 00:23:01.222254

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '700bc6d75c54'
down_revision = '05b2198969b5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Resource', 'user_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Resource', sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
