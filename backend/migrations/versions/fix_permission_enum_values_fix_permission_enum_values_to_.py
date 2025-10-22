"""Fix permission enum values to consistent format

Revision ID: fix_permission_enum_values
Revises: add_chat_only_permission
Create Date: 2025-06-27 14:02:05.870852

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_permission_enum_values'
down_revision = 'add_chat_only_permission'
branch_labels = None
depends_on = None


def upgrade():
    # Create new enum type with correct values
    op.execute("CREATE TYPE permissiontype_new AS ENUM ('permission-not-allowed', 'permission-chat-only', 'permission-read-only', 'permission-full')")
    
    # Update the column to use the new enum type with value mapping
    op.execute("""
        ALTER TABLE catalog_users 
        ALTER COLUMN permission TYPE permissiontype_new 
        USING CASE 
            WHEN permission::text = 'NOT_ALLOWED' THEN 'permission-not-allowed'::permissiontype_new
            WHEN permission::text = 'READ_ONLY' THEN 'permission-read-only'::permissiontype_new  
            WHEN permission::text = 'FULL' THEN 'permission-full'::permissiontype_new
            WHEN permission::text = 'permission-chat-only' THEN 'permission-chat-only'::permissiontype_new
            ELSE 'permission-not-allowed'::permissiontype_new
        END
    """)
    
    # Drop the old enum type and rename the new one
    op.execute("DROP TYPE permissiontype")
    op.execute("ALTER TYPE permissiontype_new RENAME TO permissiontype")


def downgrade():
    # Note: This downgrade is destructive and will lose the CHAT_ONLY permissions
    # Update data back to old format
    op.execute("UPDATE catalog_users SET permission = 'NOT_ALLOWED' WHERE permission = 'permission-not-allowed'")
    op.execute("UPDATE catalog_users SET permission = 'READ_ONLY' WHERE permission = 'permission-read-only'")
    op.execute("UPDATE catalog_users SET permission = 'FULL' WHERE permission = 'permission-full'")
    # CHAT_ONLY permissions will be lost and converted to READ-only
    op.execute("UPDATE catalog_users SET permission = 'READ_ONLY' WHERE permission = 'permission-chat-only'")
    
    # Recreate old enum type
    op.execute("CREATE TYPE permissiontype_old AS ENUM ('NOT_ALLOWED', 'READ_ONLY', 'FULL')")
    op.execute("ALTER TABLE catalog_users ALTER COLUMN permission TYPE permissiontype_old USING permission::text::permissiontype_old")
    op.execute("DROP TYPE permissiontype")
    op.execute("ALTER TYPE permissiontype_old RENAME TO permissiontype")
