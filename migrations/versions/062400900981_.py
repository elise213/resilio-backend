"""empty message

Revision ID: 062400900981
Revises: c503970bede1
Create Date: 2023-09-18 17:29:45.711366

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '062400900981'
down_revision = 'c503970bede1'
branch_labels = None
depends_on = None


def upgrade():
    # Columns already converted, no need to alter the table
    pass


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('Resource', schema=None) as batch_op:
        batch_op.alter_column('longitude',
                              existing_type=sa.Float(),
                              type_=sa.VARCHAR(length=250),
                              existing_nullable=True)
        batch_op.alter_column('latitude',
                              existing_type=sa.Float(),
                              type_=sa.VARCHAR(length=250),
                              existing_nullable=True)

    # ### end Alembic commands ###
