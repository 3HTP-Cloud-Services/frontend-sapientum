#!/bin/bash

# Script to create the UpdateCatalogDB Lambda function
# Connects to Lightsail PostgreSQL over public internet (same as backend Lambda)

set -e

echo "======================================"
echo "Creating UpdateCatalogDB Lambda Function"
echo "======================================"

# Configuration
REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-AdministratorAccess-369595298303}"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FUNCTION_NAME="UpdateCatalogDB"
ROLE_NAME="UpdateCatalogDBLambdaRole"

# Database credentials (from secret)
DB_HOST="ls-eb9991849554d7a39574d1702f3b8b996cb26c00.coaaabusiits.us-east-1.rds.amazonaws.com"
DB_PORT="5432"
DB_NAME="postgres"
DB_USER="sapientum_user"
DB_PASSWORD='aNs>4OkYTVWVsWJXYMj&hrEpA_A;YH0M'

# Set profile flag
PROFILE_FLAG=""
if [ -n "$AWS_PROFILE" ]; then
    PROFILE_FLAG="--profile $AWS_PROFILE"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "Using AWS Profile: ${AWS_PROFILE:-default}"
echo "Region: $REGION"
echo "Database: Lightsail sapientum-db (public access)"
echo ""

# Check if function already exists
echo "Checking if Lambda function already exists..."
EXISTING_FUNCTION=$(aws lambda get-function $PROFILE_FLAG --function-name $FUNCTION_NAME --region $REGION 2>/dev/null || echo "")

if [ -n "$EXISTING_FUNCTION" ]; then
    echo -e "${YELLOW}Lambda function $FUNCTION_NAME already exists!${NC}"
    read -p "Do you want to update it? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping. Run ./deploy-lambdas.sh to update the code."
        exit 0
    fi
    UPDATE_MODE=true
else
    UPDATE_MODE=false
fi

# Create IAM role if it doesn't exist (only if not in update mode)
if [ "$UPDATE_MODE" = false ]; then
    echo ""
    echo "Setting up IAM role..."
    ROLE_ARN=$(aws iam get-role $PROFILE_FLAG --role-name $ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")

    if [ -z "$ROLE_ARN" ]; then
        echo "Creating IAM role..."
        TRUST_POLICY='{
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Principal": {
                "Service": "lambda.amazonaws.com"
              },
              "Action": "sts:AssumeRole"
            }
          ]
        }'

        ROLE_ARN=$(aws iam create-role $PROFILE_FLAG \
            --role-name $ROLE_NAME \
            --assume-role-policy-document "$TRUST_POLICY" \
            --description "Role for UpdateCatalogDB Lambda" \
            --query 'Role.Arn' \
            --output text)

        echo -e "${GREEN}✓${NC} Created IAM role: $ROLE_ARN"

        # Attach managed policy for basic Lambda execution
        echo "Attaching IAM policies..."
        aws iam attach-role-policy $PROFILE_FLAG \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

        echo -e "${GREEN}✓${NC} Attached managed policies"
        echo "Waiting 10 seconds for IAM role to propagate..."
        sleep 10
    else
        echo -e "${GREEN}✓${NC} Using existing IAM role: $ROLE_ARN"
    fi
fi

# Package the Lambda function
echo ""
echo "Packaging Lambda function..."
cd "$SCRIPT_DIR/update_catalog_db"
# Clean up old dependencies first
rm -rf pg8000* requests* certifi* charset_normalizer* idna* urllib3* scramp* asn1crypto*
pip3 install -r requirements.txt -t . --quiet --upgrade
zip -r function.zip . > /dev/null
echo -e "${GREEN}✓${NC} Created deployment package"

# Create or update Lambda function
echo ""
if [ "$UPDATE_MODE" = false ]; then
    echo "Creating Lambda function..."
    aws lambda create-function $PROFILE_FLAG \
        --function-name $FUNCTION_NAME \
        --runtime python3.11 \
        --role $ROLE_ARN \
        --handler lambda_function.lambda_handler \
        --zip-file fileb://function.zip \
        --timeout 30 \
        --memory-size 256 \
        --region $REGION \
        --architectures arm64 \
        --description "Updates catalog in database with kb_name and data_source_name" \
        --environment "Variables={DB_HOST=$DB_HOST,DB_PORT=$DB_PORT,DB_NAME=$DB_NAME,DB_USER=$DB_USER,DB_PASSWORD=$DB_PASSWORD}" > /dev/null

    echo -e "${GREEN}✓${NC} Created Lambda function: $FUNCTION_NAME"
else
    echo "Updating Lambda function code and configuration..."
    aws lambda update-function-code $PROFILE_FLAG \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://function.zip \
        --region $REGION > /dev/null

    # Update environment variables
    aws lambda update-function-configuration $PROFILE_FLAG \
        --function-name $FUNCTION_NAME \
        --environment "Variables={DB_HOST=$DB_HOST,DB_PORT=$DB_PORT,DB_NAME=$DB_NAME,DB_USER=$DB_USER,DB_PASSWORD=$DB_PASSWORD}" \
        --region $REGION > /dev/null

    echo -e "${GREEN}✓${NC} Updated Lambda function: $FUNCTION_NAME"
fi

rm function.zip
cd "$SCRIPT_DIR"

echo ""
echo "======================================"
echo -e "${GREEN}UpdateCatalogDB Lambda Created Successfully!${NC}"
echo "======================================"
echo ""
echo "Lambda Function: $FUNCTION_NAME"
echo "Database: Lightsail sapientum-db (public connection, no VPC)"
echo ""
echo "Next steps:"
echo "1. Run ./deploy-step-function.sh to create the Step Function"
echo ""
