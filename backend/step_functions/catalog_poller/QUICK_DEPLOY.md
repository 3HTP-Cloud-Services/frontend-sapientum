# Quick Deployment Guide

Use these scripts to deploy the Catalog Status Poller system.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.11+
- pip3

## Deployment Steps

### 1. Deploy Lambda Functions

```bash
cd backend/step_functions/catalog_poller
./update-steps.sh
```

This will:
- Package both Lambda functions with dependencies
- Deploy CheckCatalogStatus Lambda (fully automatic)
- Update UpdateCatalogDB Lambda if it exists

**Note**: UpdateCatalogDB requires manual VPC setup on first deployment.

### 2. Set Up UpdateCatalogDB (First Time Only)

If UpdateCatalogDB doesn't exist, create it manually:

1. Go to AWS Lambda Console
2. Create function named `UpdateCatalogDB`
3. Runtime: Python 3.11
4. Upload: `lambda_packages/update_db.zip` (created by update-steps.sh)
5. Handler: `lambda_function.lambda_handler`
6. **VPC Configuration**: Same VPC as your RDS database
7. **Environment Variables**:
   ```
   DB_HOST=your-rds-host.amazonaws.com
   DB_PORT=5432
   DB_NAME=your_database
   DB_USER=your_user
   DB_PASSWORD=your_password
   ```
8. **Security Group**: Allow access to RDS
9. Timeout: 30 seconds
10. Memory: 256 MB

### 3. Create Step Function

```bash
./create-step-function.sh
```

This will:
- Create IAM role for Step Function
- Create or update the state machine
- Output the Step Function ARN

### 4. Configure Backend

Add the Step Function ARN to your backend Lambda environment variables:

```bash
aws lambda update-function-configuration \
  --function-name YourBackendFunction \
  --environment Variables="{CATALOG_POLLER_STEP_FUNCTION_ARN=arn:aws:states:REGION:ACCOUNT:stateMachine:CatalogStatusPollerStateMachine}"
```

Or add it to your Lambda configuration in AWS Console.

### 5. Grant Backend Permissions

Your backend Lambda needs permission to start Step Function executions:

```bash
aws iam put-role-policy \
  --role-name YourBackendLambdaRole \
  --policy-name AllowStepFunctionExecution \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "states:StartExecution",
      "Resource": "arn:aws:states:*:*:stateMachine:CatalogStatusPollerStateMachine"
    }]
  }'
```

## Updating Later

To update the Lambda functions after code changes:

```bash
./update-steps.sh
```

To update the Step Function state machine:

```bash
./create-step-function.sh
```

## Testing

Create a catalog via your API and check:

1. **Backend Logs**: Look for "TRIGGERING CATALOG STATUS POLLER STEP FUNCTION"
2. **Step Functions Console**: View execution progress
3. **CloudWatch Logs**: Check Lambda logs for details

## Environment Variables Reference

### Backend Lambda
```
CATALOG_POLLER_STEP_FUNCTION_ARN=arn:aws:states:REGION:ACCOUNT:stateMachine:CatalogStatusPollerStateMachine
```

### UpdateCatalogDB Lambda
```
DB_HOST=your-rds-host.amazonaws.com
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
```

## AWS Resources Created

- ✅ Lambda: `CheckCatalogStatus`
- ✅ Lambda: `UpdateCatalogDB`
- ✅ IAM Role: `CheckCatalogStatusLambdaRole`
- ✅ IAM Role: `CatalogStatusPollerStepFunctionRole`
- ✅ Step Function: `CatalogStatusPollerStateMachine`

## Cost

Per catalog creation: ~$0.008 (less than 1 cent)

## Troubleshooting

**update-steps.sh fails with "command not found"**
- Make script executable: `chmod +x update-steps.sh`

**"Error: AWS CLI is not installed"**
- Install AWS CLI: https://aws.amazon.com/cli/

**"UpdateCatalogDB needs manual setup"**
- Follow step 2 above to create the Lambda function

**Step Function not triggering**
- Check backend has environment variable set
- Verify backend Lambda has permissions to start executions

**Database update fails**
- Check VPC configuration of UpdateCatalogDB Lambda
- Verify security groups allow Lambda → RDS
- Check database credentials in environment variables
