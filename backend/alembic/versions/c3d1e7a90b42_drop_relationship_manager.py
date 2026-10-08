"""drop relationship manager column

Revision ID: c3d1e7a90b42
Revises: bf80d2937990
Create Date: 2026-10-07 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d1e7a90b42'
down_revision: Union[str, None] = 'bf80d2937990'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('customers') as batch:
        batch.drop_index('ix_customers_relationship_manager_id')
        batch.drop_column('relationship_manager_id')


def downgrade() -> None:
    with op.batch_alter_table('customers') as batch:
        batch.add_column(sa.Column('relationship_manager_id', sa.String(length=50), nullable=True))
        batch.create_index('ix_customers_relationship_manager_id', ['relationship_manager_id'])
