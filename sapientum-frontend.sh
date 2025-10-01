#!/bin/bash

set -e

AWS_PROFILE="AdministratorAccess-369595298303"
S3_BUCKET="s3-frontend-3htp-sapientum-ai"
CLOUDFRONT_DISTRIBUTION_ID="E1KB6ETEXV7TWJ"

echo "Building static frontend..."
make static

echo "Uploading to S3 bucket: $S3_BUCKET..."
aws s3 sync backend/static/ s3://$S3_BUCKET/ --profile $AWS_PROFILE --delete

echo "Creating CloudFront invalidation..."
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
  --paths "/*" \
  --profile $AWS_PROFILE

echo "Deployment complete!"
echo "Site: https://sapientum-app.3htp.cloud"
