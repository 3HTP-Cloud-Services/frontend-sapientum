#!/bin/bash

# Script to deploy/update Lambda functions for Catalog Status Poller
# This script packages and deploys both Lambda functions from the main project directory

set -e

echo "======================================"
echo "Deploying Catalog Status Poller Lambda Functions"
echo "======================================"

# Configuration
REGION="${AWS_REGION:-us-east-1}"
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../.." && pwd )"
CHECK_STATUS_DIR="$PROJECT_ROOT/check_catalog_status"
UPDATE_DB_DIR="$PROJECT_ROOT/update_catalog_db"

# Lambda configuration
CHECK_STATUS_FUNCTION_NAME="CheckCatalogStatus"
UPDATE_DB_FUNCTION_NAME="UpdateCatalogDB"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

echo "AWS Region: $REGION"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Verify Lambda directories exist
if [ ! -d "$CHECK_STATUS_DIR" ]; then
    echo -e "${RED}Error: $CHECK_STATUS_DIR not found${NC}"
    exit 1
fi

if [ ! -d "$UPDATE_DB_DIR" ]; then
    echo -e "${RED}Error: $UPDATE_DB_DIR not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found Lambda function directories"
echo ""

# ========================================
# Deploy CheckCatalogStatus Lambda
# ========================================
echo -e "${BLUE}[1/2] Deploying CheckCatalogStatus Lambda...${NC}"

cd "$CHECK_STATUS_DIR"

# Check if function exists
CHECK_STATUS_EXISTS=$(aws lambda get-function --function-name $CHECK_STATUS_FUNCTION_NAME --region $REGION 2>/dev/null || echo "")

if [ -z "$CHECK_STATUS_EXISTS" ]; then
    echo "Creating new Lambda function..."

    # Create IAM role if it doesn't exist
    CHECK_STATUS_ROLE_NAME="CheckCatalogStatusLambdaRole"
    CHECK_STATUS_ROLE_ARN=$(aws iam get-role --role-name $CHECK_STATUS_ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")

    if [ -z "$CHECK_STATUS_ROLE_ARN" ]; then
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

        CHECK_STATUS_ROLE_ARN=$(aws iam create-role \
            --role-name $CHECK_STATUS_ROLE_NAME \
            --assume-role-policy-document "$TRUST_POLICY" \
            --description "Role for CheckCatalogStatus Lambda" \
            --query 'Role.Arn' \
            --output text)

        aws iam attach-role-policy \
            --role-name $CHECK_STATUS_ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

        echo "Waiting 10 seconds for IAM role to propagate..."
        sleep 10
    fi

    # Package and deploy
    echo "Packaging Lambda function..."
    pip3 install -r requirements.txt -t . --quiet --upgrade
    zip -r function.zip . > /dev/null

    aws lambda create-function \
        --function-name $CHECK_STATUS_FUNCTION_NAME \
        --runtime python3.11 \
        --role $CHECK_STATUS_ROLE_ARN \
        --handler lambda_function.lambda_handler \
        --zip-file fileb://function.zip \
        --timeout 60 \
        --memory-size 256 \
        --region $REGION \
        --description "Checks catalog status from external API" > /dev/null

    rm function.zip
    echo -e "${GREEN}✓${NC} Created CheckCatalogStatus Lambda function"
else
    echo "Updating existing Lambda function..."
    pip3 install -r requirements.txt -t . --quiet --upgrade
    zip -r function.zip . > /dev/null

    aws lambda update-function-code \
        --function-name $CHECK_STATUS_FUNCTION_NAME \
        --zip-file fileb://function.zip \
        --region $REGION > /dev/null

    rm function.zip
    echo -e "${GREEN}✓${NC} Updated CheckCatalogStatus Lambda function"
fi

echo ""

# ========================================
# Deploy UpdateCatalogDB Lambda
# ========================================
echo -e "${BLUE}[2/2] Deploying UpdateCatalogDB Lambda...${NC}"

cd "$UPDATE_DB_DIR"

# Check if function exists
UPDATE_DB_EXISTS=$(aws lambda get-function --function-name $UPDATE_DB_FUNCTION_NAME --region $REGION 2>/dev/null || echo "")

if [ -z "$UPDATE_DB_EXISTS" ]; then
    echo -e "${YELLOW}Warning: UpdateCatalogDB Lambda does not exist${NC}"
    echo "This Lambda requires:"
    echo "  - VPC configuration (same VPC as RDS)"
    echo "  - Environment variables (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)"
    echo "  - Security groups allowing access to RDS"
    echo ""

    # Create package anyway for manual deployment
    echo "Creating deployment package..."
    pip3 install -r requirements.txt -t . --quiet --upgrade
    zip -r function.zip . > /dev/null
    echo -e "${GREEN}✓${NC} Package created: $UPDATE_DB_DIR/function.zip"
    echo "Upload this manually in AWS Console with VPC configuration"
    echo ""
    echo -e "${YELLOW}Skipping UpdateCatalogDB deployment${NC}"
else
    echo "Updating existing Lambda function..."
    pip3 install -r requirements.txt -t . --quiet --upgrade
    zip -r function.zip . > /dev/null

    aws lambda update-function-code \
        --function-name $UPDATE_DB_FUNCTION_NAME \
        --zip-file fileb://function.zip \
        --region $REGION > /dev/null

    rm function.zip
    echo -e "${GREEN}✓${NC} Updated UpdateCatalogDB Lambda function"
fi

echo ""
echo "======================================"
echo -e "${GREEN}Lambda Functions Deployment Complete!${NC}"
echo "======================================"
echo ""
echo "Deployed/Updated:"
echo -e "  ${GREEN}✓${NC} CheckCatalogStatus"

if [ -z "$UPDATE_DB_EXISTS" ]; then
    echo -e "  ${YELLOW}⚠${NC} UpdateCatalogDB (package ready for manual setup)"
else
    echo -e "  ${GREEN}✓${NC} UpdateCatalogDB"
fi

echo ""
echo "Next steps:"
echo "1. Run create-step-function.sh to create/update the Step Function"
echo "2. Update your backend Lambda with the Step Function ARN"
echo ""
echo "Done!"
