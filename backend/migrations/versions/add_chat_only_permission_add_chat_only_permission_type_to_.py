"""Add CHAT_ONLY permission type to PermissionType enum

Revision ID: add_chat_only_permission
Revises: 1750877134
Create Date: 2025-06-27 13:38:57.007731

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_chat_only_permission'
down_revision = '1750877134'
branch_labels = None
depends_on = None


def upgrade():
    # Add CHAT_ONLY enum value to PermissionType
    op.execute("ALTER TYPE permissiontype ADD VALUE 'permission-chat-only'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values, so this is a no-op
    pass
