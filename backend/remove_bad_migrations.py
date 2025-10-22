#!/usr/bin/env python3
"""
Script to remove problematic files from migrations/versions directory.
These files are not proper Flask migration files.
"""
import os

# Files to remove from migrations/versions directory
files_to_remove = [
    "analyze_migrations.py",
    "delete_merge_heads.py", 
    "merge_heads_12345678.py",
    "self_deleting_script.py"
]

# Base directory
base_dir = os.path.join(os.path.dirname(__file__), "migrations", "versions")

print(f"Looking for files to remove in: {base_dir}")

for filename in files_to_remove:
    file_path = os.path.join(base_dir, filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✓ Removed: {filename}")
        else:
            print(f"- File not found: {filename}")
    except Exception as e:
        print(f"✗ Error removing {filename}: {e}")

print("\nCleanup complete!")

# Verify the files are gone
print("\nVerifying files were removed:")
for filename in files_to_remove:
    file_path = os.path.join(base_dir, filename)
    exists = os.path.exists(file_path)
    status = "STILL EXISTS" if exists else "REMOVED"
    print(f"  {filename}: {status}")