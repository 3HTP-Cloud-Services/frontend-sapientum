# Catalog Status Poller

This Step Function implementation polls the external catalog API until the catalog is fully provisioned with a valid `kb_name` and `data_source_name`, then updates the local database.

## Files

- **`check_catalog_status.py`**: Lambda function that checks catalog status via external API
- **`update_catalog_db.py`**: Lambda function that updates the catalog in the database
- **`state_machine.json`**: Step Function state machine definition
- **`requirements.txt`**: Python dependencies for Lambda functions
- **`DEPLOYMENT.md`**: Detailed deployment instructions

## How It Works

1. **Catalog Creation**: When a catalog is created via `/api/catalogs` endpoint:
   - External API is called to create the catalog
   - Local database record is created
   - Step Function is triggered automatically

2. **Polling Loop** (Step Function):
   - Calls `CheckCatalogStatus` Lambda every 20 seconds
   - Checks if `kb_name` and `data_source_name` are valid (not PENDING/NULL/empty)
   - Continues polling for up to 150 attempts (50 minutes)

3. **Database Update**:
   - Once catalog is ready, calls `UpdateCatalogDB` Lambda
   - Updates `knowledge_base_id` and `data_source_id` columns
   - Marks process as complete

## Key Features

- ✅ **Automatic polling**: No manual intervention required
- ✅ **Resilient**: Handles API errors and retries automatically
- ✅ **Time-bounded**: Maximum 50 minutes before timeout
- ✅ **Observable**: Full CloudWatch logging for debugging
- ✅ **Cost-effective**: ~$0.008 per catalog creation

## State Machine Flow

```
Start
  ↓
CheckCatalogStatus (Lambda)
  ↓
Is Catalog Ready?
  ├─ Yes → UpdateCatalogInDB (Lambda) → Success
  └─ No → Check Max Attempts
            ├─ < 150 → Wait 20s → CheckCatalogStatus (loop)
            └─ ≥ 150 → MaxAttemptsReached (fail)
```

## Environment Variables Required

### For Backend (Flask/Lambda)
- `CATALOG_POLLER_STEP_FUNCTION_ARN`: ARN of the Step Function state machine

### For UpdateCatalogDB Lambda
- `DB_HOST`: PostgreSQL host
- `DB_PORT`: PostgreSQL port (default: 5432)
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password

## Lambda Function Specifications

### CheckCatalogStatus
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 60 seconds
- **Dependencies**: requests

### UpdateCatalogDB
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Dependencies**: psycopg2-binary
- **VPC**: Must be in same VPC as RDS

## Quick Start

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete deployment instructions.

## Monitoring

View execution logs in CloudWatch:
- `/aws/lambda/CheckCatalogStatus`
- `/aws/lambda/UpdateCatalogDB`
- Step Functions execution history in AWS Console

## Troubleshooting

Common issues and solutions:

1. **Step Function not triggering**
   - Check `CATALOG_POLLER_STEP_FUNCTION_ARN` is set
   - Verify IAM permissions for Step Function execution

2. **Polling times out**
   - External API may be slow
   - Consider increasing max attempts or wait time

3. **Database update fails**
   - Check Lambda VPC configuration
   - Verify database credentials
   - Ensure security groups allow Lambda → RDS connection

For more troubleshooting, see [DEPLOYMENT.md](./DEPLOYMENT.md#troubleshooting).
