"""Add telegram_id field

Revision ID: 3c79b959e7e0
Revises: 3830f318eb95
Create Date: 2024-10-24 16:09:37.557381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c79b959e7e0'
down_revision: Union[str, None] = '3830f318eb95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clients', sa.Column('telegram_id', sa.Integer(), nullable=False))
    op.create_unique_constraint(None, 'clients', ['telegram_id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'clients', type_='unique')
    op.drop_column('clients', 'telegram_id')
    # ### end Alembic commands ###