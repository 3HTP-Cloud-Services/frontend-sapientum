#!/bin/bash

# Script to create the Catalog Status Poller Step Function State Machine
# Run from the main project directory: /Users/jpnunez/3htp/SapientumAI

set -e

echo "======================================"
echo "Creating Catalog Status Poller Step Function"
echo "======================================"

# Configuration
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID="${AWS_ACCOUNT_ID}"
AWS_PROFILE="${AWS_PROFILE:-AdministratorAccess-369595298303}"
STATE_MACHINE_NAME="CatalogStatusPollerStateMachine"
ROLE_NAME="CatalogStatusPollerStepFunctionRole"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
STATE_MACHINE_FILE="$SCRIPT_DIR/backend/step_functions/catalog_poller/state_machine.json"

# Set profile flag if profile is specified
PROFILE_FLAG=""
if [ -n "$AWS_PROFILE" ]; then
    PROFILE_FLAG="--profile $AWS_PROFILE"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Get AWS Account ID if not provided
if [ -z "$ACCOUNT_ID" ]; then
    echo "Getting AWS Account ID..."
    ACCOUNT_ID=$(aws sts get-caller-identity $PROFILE_FLAG --query Account --output text)
    if [ -z "$ACCOUNT_ID" ]; then
        echo -e "${RED}Error: Could not determine AWS Account ID${NC}"
        exit 1
    fi
fi

echo "Using AWS Profile: ${AWS_PROFILE:-default}"

echo "AWS Region: $REGION"
echo "AWS Account ID: $ACCOUNT_ID"
echo ""

# Check if Lambda functions exist
echo "Checking if required Lambda functions exist..."
CHECK_STATUS_LAMBDA_ARN=$(aws lambda get-function $PROFILE_FLAG --function-name CheckCatalogStatus --region $REGION --query 'Configuration.FunctionArn' --output text 2>/dev/null || echo "")
UPDATE_DB_LAMBDA_ARN=$(aws lambda get-function $PROFILE_FLAG --function-name UpdateCatalogDB --region $REGION --query 'Configuration.FunctionArn' --output text 2>/dev/null || echo "")

if [ -z "$CHECK_STATUS_LAMBDA_ARN" ]; then
    echo -e "${YELLOW}Warning: CheckCatalogStatus Lambda function not found${NC}"
    echo "Please deploy Lambda functions using ./deploy-lambdas.sh first"
    exit 1
fi

if [ -z "$UPDATE_DB_LAMBDA_ARN" ]; then
    echo -e "${YELLOW}Warning: UpdateCatalogDB Lambda function not found${NC}"
    echo "This Lambda requires manual VPC setup (see deploy-lambdas.sh output)"
    echo ""
    read -p "Continue without UpdateCatalogDB? Step Function will fail at database update. (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled. Please create UpdateCatalogDB Lambda first."
        exit 1
    fi
    # Use a placeholder ARN for now
    UPDATE_DB_LAMBDA_ARN="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:UpdateCatalogDB"
    echo -e "${YELLOW}Using placeholder ARN - you must create this Lambda before the Step Function can work${NC}"
fi

echo -e "${GREEN}✓${NC} CheckCatalogStatus Lambda found: $CHECK_STATUS_LAMBDA_ARN"
echo -e "${GREEN}✓${NC} UpdateCatalogDB Lambda found: $UPDATE_DB_LAMBDA_ARN"
echo ""

# Create IAM role for Step Function if it doesn't exist
echo "Checking if IAM role exists..."
ROLE_ARN=$(aws iam get-role $PROFILE_FLAG --role-name $ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
    echo "Creating IAM role for Step Function..."

    # Create trust policy
    TRUST_POLICY='{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "states.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }'

    # Create role
    ROLE_ARN=$(aws iam create-role $PROFILE_FLAG \
        --role-name $ROLE_NAME \
        --assume-role-policy-document "$TRUST_POLICY" \
        --description "Role for Catalog Status Poller Step Function" \
        --query 'Role.Arn' \
        --output text)

    echo -e "${GREEN}✓${NC} Created IAM role: $ROLE_ARN"

    # Create and attach inline policy
    ROLE_POLICY='{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "lambda:InvokeFunction"
          ],
          "Resource": [
            "'"$CHECK_STATUS_LAMBDA_ARN"'",
            "'"$UPDATE_DB_LAMBDA_ARN"'"
          ]
        },
        {
          "Effect": "Allow",
          "Action": [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ],
          "Resource": "arn:aws:logs:*:*:*"
        }
      ]
    }'

    aws iam put-role-policy $PROFILE_FLAG \
        --role-name $ROLE_NAME \
        --policy-name "CatalogStatusPollerPolicy" \
        --policy-document "$ROLE_POLICY"

    echo -e "${GREEN}✓${NC} Attached policy to role"
    echo "Waiting 10 seconds for IAM role to propagate..."
    sleep 10
else
    echo -e "${GREEN}✓${NC} IAM role already exists: $ROLE_ARN"
fi

echo ""

# Update state machine definition with correct ARNs
echo "Preparing state machine definition..."
STATE_MACHINE_DEF=$(cat "$STATE_MACHINE_FILE" | \
    sed "s|arn:aws:lambda:REGION:ACCOUNT_ID:function:CheckCatalogStatus|$CHECK_STATUS_LAMBDA_ARN|g" | \
    sed "s|arn:aws:lambda:REGION:ACCOUNT_ID:function:UpdateCatalogDB|$UPDATE_DB_LAMBDA_ARN|g")

# Check if state machine already exists
EXISTING_STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines $PROFILE_FLAG \
    --region $REGION \
    --query "stateMachines[?name=='$STATE_MACHINE_NAME'].stateMachineArn" \
    --output text 2>/dev/null || echo "")

if [ -z "$EXISTING_STATE_MACHINE_ARN" ]; then
    # Create new state machine
    echo "Creating Step Function state machine..."
    STATE_MACHINE_ARN=$(aws stepfunctions create-state-machine $PROFILE_FLAG \
        --name $STATE_MACHINE_NAME \
        --definition "$STATE_MACHINE_DEF" \
        --role-arn $ROLE_ARN \
        --region $REGION \
        --query 'stateMachineArn' \
        --output text)

    echo -e "${GREEN}✓${NC} Created Step Function: $STATE_MACHINE_ARN"
else
    # Update existing state machine
    echo "Updating existing Step Function state machine..."
    STATE_MACHINE_ARN=$(aws stepfunctions update-state-machine $PROFILE_FLAG \
        --state-machine-arn $EXISTING_STATE_MACHINE_ARN \
        --definition "$STATE_MACHINE_DEF" \
        --role-arn $ROLE_ARN \
        --region $REGION \
        --query 'updateDate' \
        --output text)

    STATE_MACHINE_ARN=$EXISTING_STATE_MACHINE_ARN
    echo -e "${GREEN}✓${NC} Updated Step Function: $STATE_MACHINE_ARN"
fi

echo ""
echo "======================================"
echo -e "${GREEN}Step Function Created Successfully!${NC}"
echo "======================================"
echo ""
echo "State Machine ARN:"
echo "$STATE_MACHINE_ARN"
echo ""
echo "Next steps:"
echo "1. Add this ARN to your backend Lambda environment variables:"
echo "   CATALOG_POLLER_STEP_FUNCTION_ARN=$STATE_MACHINE_ARN"
echo ""
echo "2. Grant your backend Lambda permission to start executions:"
echo "   aws iam put-role-policy $PROFILE_FLAG --role-name <YourBackendLambdaRole> --policy-name AllowStepFunctionExecution --policy-document '{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"states:StartExecution\",\"Resource\":\"$STATE_MACHINE_ARN\"}]}'"
echo ""
echo "3. Test the Step Function in AWS Console:"
echo "   https://console.aws.amazon.com/states/home?region=$REGION#/statemachines/view/$STATE_MACHINE_ARN"
echo ""
