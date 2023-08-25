"""empty message

Revision ID: c503970bede1
Revises: be254c492b6f
Create Date: 2023-08-21 17:48:09.842720

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c503970bede1'
down_revision = 'be254c492b6f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('Resource', schema=None) as batch_op:
        batch_op.alter_column('description',
               existing_type=sa.VARCHAR(length=500),
               type_=sa.String(length=900),
               existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('Resource', schema=None) as batch_op:
        batch_op.alter_column('description',
               existing_type=sa.String(length=900),
               type_=sa.VARCHAR(length=500),
               existing_nullable=True)

    # ### end Alembic commands ###
