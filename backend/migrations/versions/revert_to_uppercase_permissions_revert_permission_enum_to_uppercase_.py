"""Revert permission enum to uppercase format

Revision ID: revert_to_uppercase_permissions
Revises: fix_permission_enum_values
Create Date: 2025-06-27 14:07:44.926673

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'revert_to_uppercase_permissions'
down_revision = 'fix_permission_enum_values'
branch_labels = None
depends_on = None


def upgrade():
    # Create new enum type with uppercase values
    op.execute("CREATE TYPE permissiontype_new AS ENUM ('NOT_ALLOWED', 'CHAT_ONLY', 'READ_ONLY', 'FULL')")
    
    # Update the column to use the new enum type with value mapping
    op.execute("""
        ALTER TABLE catalog_users 
        ALTER COLUMN permission TYPE permissiontype_new 
        USING CASE 
            WHEN permission::text = 'permission-not-allowed' THEN 'NOT_ALLOWED'::permissiontype_new
            WHEN permission::text = 'permission-chat-only' THEN 'CHAT_ONLY'::permissiontype_new
            WHEN permission::text = 'permission-read-only' THEN 'READ_ONLY'::permissiontype_new  
            WHEN permission::text = 'permission-full' THEN 'FULL'::permissiontype_new
            ELSE 'NOT_ALLOWED'::permissiontype_new
        END
    """)
    
    # Drop the old enum type and rename the new one
    op.execute("DROP TYPE permissiontype")
    op.execute("ALTER TYPE permissiontype_new RENAME TO permissiontype")


def downgrade():
    # Revert back to lowercase format
    op.execute("CREATE TYPE permissiontype_old AS ENUM ('permission-not-allowed', 'permission-chat-only', 'permission-read-only', 'permission-full')")
    
    op.execute("""
        ALTER TABLE catalog_users 
        ALTER COLUMN permission TYPE permissiontype_old 
        USING CASE 
            WHEN permission::text = 'NOT_ALLOWED' THEN 'permission-not-allowed'::permissiontype_old
            WHEN permission::text = 'CHAT_ONLY' THEN 'permission-chat-only'::permissiontype_old
            WHEN permission::text = 'READ_ONLY' THEN 'permission-read-only'::permissiontype_old
            WHEN permission::text = 'FULL' THEN 'permission-full'::permissiontype_old
            ELSE 'permission-not-allowed'::permissiontype_old
        END
    """)
    
    op.execute("DROP TYPE permissiontype")
    op.execute("ALTER TYPE permissiontype_old RENAME TO permissiontype")
