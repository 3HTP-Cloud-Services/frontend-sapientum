# Catalog Status Poller - AWS Step Function Deployment Guide

This guide explains how to deploy the catalog status polling system using AWS Step Functions and Lambda.

## Overview

When a catalog is created, the system triggers a Step Function that:
1. Polls the external API every 20 seconds to check catalog status
2. Waits until `kb_name` and `data_source_name` are available
3. Updates the local database with these values
4. Times out after 150 attempts (50 minutes)

## Architecture

```
Catalog Creation (Flask)
    ↓
Triggers Step Function
    ↓
┌─────────────────────────────────────┐
│ Step Function State Machine         │
│ ┌─────────────────────────────────┐ │
│ │ 1. CheckCatalogStatus (Lambda)  │ │
│ │    - Calls external GET API     │ │
│ │    - Checks kb_name & ds_name   │ │
│ └─────────────────────────────────┘ │
│              ↓                       │
│ ┌─────────────────────────────────┐ │
│ │ 2. Is Catalog Ready? (Choice)   │ │
│ └─────────────────────────────────┘ │
│         ↓ No        ↓ Yes           │
│    ┌─────┐    ┌──────────────────┐ │
│    │Wait │    │ UpdateCatalogInDB│ │
│    │20s │    │     (Lambda)     │ │
│    └─────┘    └──────────────────┘ │
│      ↓ Loop          ↓              │
│    (max 150x)    Success            │
└─────────────────────────────────────┘
```

## Deployment Steps

### 1. Create Lambda Functions

#### a. CheckCatalogStatus Lambda

```bash
# Create deployment package
cd /path/to/backend/step_functions/catalog_poller
mkdir -p lambda_packages/check_status
pip install -r requirements.txt -t lambda_packages/check_status/
cp check_catalog_status.py lambda_packages/check_status/lambda_function.py
cd lambda_packages/check_status
zip -r ../check_status.zip .
```

Create Lambda in AWS Console or CLI:
- **Function name**: `CheckCatalogStatus`
- **Runtime**: Python 3.11
- **Handler**: `lambda_function.lambda_handler`
- **Timeout**: 60 seconds
- **Memory**: 256 MB
- **IAM Role**: Create role with CloudWatch Logs permissions

Upload the `check_status.zip` file.

#### b. UpdateCatalogDB Lambda

```bash
# Create deployment package
cd /path/to/backend/step_functions/catalog_poller
mkdir -p lambda_packages/update_db
pip install -r requirements.txt -t lambda_packages/update_db/
cp update_catalog_db.py lambda_packages/update_db/lambda_function.py
cd lambda_packages/update_db
zip -r ../update_db.zip .
```

Create Lambda in AWS Console or CLI:
- **Function name**: `UpdateCatalogDB`
- **Runtime**: Python 3.11
- **Handler**: `lambda_function.lambda_handler`
- **Timeout**: 30 seconds
- **Memory**: 256 MB
- **Environment Variables**:
  - `DB_HOST`: Your RDS PostgreSQL host
  - `DB_PORT`: 5432
  - `DB_NAME`: Your database name
  - `DB_USER`: Your database user
  - `DB_PASSWORD`: Your database password
- **VPC Configuration**: Attach to same VPC as RDS
- **IAM Role**: Create role with:
  - CloudWatch Logs permissions
  - VPC execution permissions (if in VPC)
  - RDS access

Upload the `update_db.zip` file.

### 2. Create Step Function State Machine

1. Go to AWS Step Functions console
2. Click "Create state machine"
3. Choose "Write your workflow in code"
4. Copy the content from `state_machine.json`
5. Replace placeholders:
   - `REGION`: Your AWS region (e.g., `us-east-1`)
   - `ACCOUNT_ID`: Your AWS account ID
6. Review the visual workflow
7. Create or select an IAM role with permissions to:
   - Invoke Lambda functions
   - Write CloudWatch Logs
8. Name: `CatalogStatusPollerStateMachine`
9. Click "Create"

### 3. Configure Backend Application

Add the Step Function ARN to your environment variables:

```bash
# For Lambda deployment
export CATALOG_POLLER_STEP_FUNCTION_ARN="arn:aws:states:REGION:ACCOUNT_ID:stateMachine:CatalogStatusPollerStateMachine"

# Or add to your deployment configuration
```

For Lambda Function URL deployment, add this to the Lambda configuration's environment variables.

### 4. Update IAM Permissions

The Flask backend's execution role needs permission to start Step Function executions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "states:StartExecution"
      ],
      "Resource": "arn:aws:states:REGION:ACCOUNT_ID:stateMachine:CatalogStatusPollerStateMachine"
    }
  ]
}
```

## Testing

### Test CheckCatalogStatus Lambda

Test event:
```json
{
  "catalog_name": "test_catalog",
  "jwt_token": "your_jwt_token_here",
  "local_catalog_id": 1,
  "attempt_count": 1
}
```

Expected output:
```json
{
  "success": true,
  "catalog_ready": false,
  "kb_name": "PENDING",
  "data_source_name": "PENDING",
  "catalog_data": {...},
  "local_catalog_id": 1,
  "catalog_name": "test_catalog",
  "attempt_count": 2
}
```

### Test UpdateCatalogDB Lambda

Test event:
```json
{
  "local_catalog_id": 1,
  "kb_name": "test_kb_12345",
  "data_source_name": "test_ds_67890",
  "catalog_name": "test_catalog"
}
```

Expected output:
```json
{
  "success": true,
  "updated": true,
  "rows_updated": 1,
  "catalog_id": 1,
  "catalog_name": "test_catalog",
  "kb_name": "test_kb_12345",
  "data_source_name": "test_ds_67890"
}
```

### Test Step Function

Start execution with:
```json
{
  "catalog_name": "test_catalog",
  "local_catalog_id": 1,
  "jwt_token": "your_jwt_token_here",
  "attempt_count": 0
}
```

Monitor the execution in the Step Functions console.

## Monitoring

### CloudWatch Logs

- **CheckCatalogStatus logs**: `/aws/lambda/CheckCatalogStatus`
- **UpdateCatalogDB logs**: `/aws/lambda/UpdateCatalogDB`
- **Step Function logs**: Configure in state machine settings

### Metrics to Monitor

1. **Step Function Executions**
   - ExecutionsStarted
   - ExecutionsSucceeded
   - ExecutionsFailed
   - ExecutionTime

2. **Lambda Invocations**
   - Invocations
   - Errors
   - Duration
   - Throttles

### Alarms

Consider setting up CloudWatch alarms for:
- Step Function execution failures
- Lambda function errors
- Execution time exceeding threshold

## Cost Estimation

For a single catalog creation:
- **Step Functions**: ~$0.025 per 1000 state transitions
  - Average: 75 state transitions (75 checks + conditional logic)
  - Cost: ~$0.002 per catalog

- **Lambda**: ~$0.0000166667 per GB-second
  - CheckCatalogStatus: 75 invocations × 2 seconds × 256MB = $0.006
  - UpdateCatalogDB: 1 invocation × 1 second × 256MB = $0.00004
  - Total Lambda: ~$0.006 per catalog

**Total cost per catalog**: ~$0.008 (less than 1 cent)

## Troubleshooting

### Step Function Never Completes

- Check CloudWatch logs for Lambda errors
- Verify JWT token is valid and not expired
- Ensure external API is accessible
- Check network connectivity from Lambda (VPC configuration)

### Database Update Fails

- Verify environment variables in UpdateCatalogDB Lambda
- Check VPC configuration and security groups
- Verify database credentials
- Check RDS is accessible from Lambda's subnet

### External API Returns Errors

- Verify JWT token is being passed correctly
- Check token permissions in external API
- Verify catalog_name matches exactly
- Check external API status

## Cleanup

To remove the deployment:
1. Delete the Step Function state machine
2. Delete both Lambda functions
3. Remove IAM roles and policies
4. Remove CloudWatch log groups (if desired)

## Future Improvements

- Add SNS notifications on success/failure
- Implement exponential backoff instead of fixed 20s intervals
- Add DynamoDB for execution state tracking
- Create dashboard for monitoring catalog creation pipeline
- Add retry logic with different JWT token refresh
