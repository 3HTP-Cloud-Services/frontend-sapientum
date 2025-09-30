#!/bin/bash

echo "Syncing shared components to frontend applications..."

# Create script directories if they don't exist
mkdir -p merged_frontend/frontend/src/shared
mkdir -p merged_frontend/embed-frontend/src/shared

# Copy shared components
cp -r merged_frontend/shared-components/* merged_frontend/frontend/src/shared/
cp -r merged_frontend/shared-components/* merged_frontend/embed-frontend/src/shared/

echo "Syncing completed!"