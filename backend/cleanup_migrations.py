#!/usr/bin/env python3
import os
import sys

# Files to remove from migrations/versions/
files_to_remove = [
    'analyze_migrations.py',
    'delete_merge_heads.py', 
    'merge_heads_12345678.py',
    'self_deleting_script.py'
]

migrations_dir = 'migrations/versions'

print("Cleaning up non-migration files from migrations/versions/...")

for filename in files_to_remove:
    file_path = os.path.join(migrations_dir, filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✅ Removed: {filename}")
        else:
            print(f"ℹ️  Not found: {filename}")
    except Exception as e:
        print(f"❌ Error removing {filename}: {e}")

print("\nCleanup complete! You can now run: flask db upgrade")