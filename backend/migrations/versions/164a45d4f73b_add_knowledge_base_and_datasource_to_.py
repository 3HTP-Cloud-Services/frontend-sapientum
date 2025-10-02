"""add_knowledge_base_and_datasource_to_catalog

Revision ID: 164a45d4f73b
Revises: 1752174611
Create Date: 2025-10-01 16:40:02.516262

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '164a45d4f73b'
down_revision = '1752174611'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('catalogs', sa.Column('knowledge_base_id', sa.String(length=50), nullable=True))
    op.add_column('catalogs', sa.Column('data_source_id', sa.String(length=50), nullable=True))

    op.execute("UPDATE catalogs SET knowledge_base_id = 'WZROVEIVGV', data_source_id = '7E1KNZRZRK'")


def downgrade():
    op.drop_column('catalogs', 'data_source_id')
    op.drop_column('catalogs', 'knowledge_base_id')
