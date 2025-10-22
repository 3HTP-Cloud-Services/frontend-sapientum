#!/bin/bash

# Script to check backend Lambda environment variables

AWS_PROFILE="${AWS_PROFILE:-AdministratorAccess-369595298303}"
PROFILE_FLAG="--profile $AWS_PROFILE"

echo "======================================"
echo "Backend Lambda Environment Variables"
echo "======================================"
echo ""

aws lambda get-function-configuration $PROFILE_FLAG \
    --region us-east-1 \
    --function-name APIGW-IA-SAPI-FlaskFunction-sZeca781RQ37 \
    --query 'Environment.Variables' \
    --output json | python3 -m json.tool

echo ""
