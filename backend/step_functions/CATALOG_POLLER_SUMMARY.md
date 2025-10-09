# Catalog Status Poller - Implementation Summary

## ✅ What Was Created

### 1. **AWS Step Function Implementation** (`/backend/step_functions/catalog_poller/`)

Files created:
- `check_catalog_status.py` - Lambda to poll external API
- `update_catalog_db.py` - Lambda to update database
- `state_machine.json` - Step Function definition
- `requirements.txt` - Python dependencies
- `DEPLOYMENT.md` - Complete deployment guide
- `README.md` - Overview and quick start
- `.gitignore` - Git ignore rules

### 2. **Backend Integration** (Updated files)

- **`backend/catalog.py`**:
  - Added `trigger_catalog_status_poller()` function
  - Triggers Step Function after catalog creation

- **`backend/app.py`**:
  - Updated `/api/catalogs` POST endpoint
  - Now triggers Step Function automatically
  - Returns execution ARN in response

## 🔄 How It Works

### Flow Diagram

```
User Creates Catalog
       ↓
POST /api/catalogs (Flask Backend)
       ↓
┌──────────────────────────────┐
│ 1. Call External API         │
│    POST /api/v1/catalogs     │
│    with apply=true           │
└──────────────────────────────┘
       ↓
┌──────────────────────────────┐
│ 2. Create Local DB Record    │
│    INSERT INTO catalog       │
└──────────────────────────────┘
       ↓
┌──────────────────────────────┐
│ 3. Trigger Step Function     │
│    Pass: catalog_name,       │
│    catalog_id, jwt_token     │
└──────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│         Step Function Loop              │
│  ┌───────────────────────────────┐     │
│  │ CheckCatalogStatus Lambda     │     │
│  │ GET /api/v1/catalogs/{name}   │     │
│  └───────────────────────────────┘     │
│              ↓                          │
│  ┌───────────────────────────────┐     │
│  │ kb_name & data_source valid?  │     │
│  └───────────────────────────────┘     │
│         No ↓      ↓ Yes                │
│    Wait 20s   UpdateCatalogDB Lambda    │
│         ↑     (UPDATE catalog SET...)   │
│         │              ↓                │
│    (Loop max        Success!            │
│     150 times)                          │
└─────────────────────────────────────────┘
```

### Key Features

1. **Automatic Polling**: Checks every 20 seconds
2. **Timeout Protection**: Max 150 attempts (50 minutes)
3. **Database Update**: Stores `kb_name` → `knowledge_base_id` and `data_source_name` → `data_source_id`
4. **Error Handling**: Graceful failures with CloudWatch logging
5. **JWT Propagation**: Passes auth token through entire flow

## 🚀 Deployment Steps (Quick Version)

### 1. Deploy Lambda Functions

```bash
cd backend/step_functions/catalog_poller

# Package check_catalog_status
mkdir -p lambda_packages/check_status
pip install -r requirements.txt -t lambda_packages/check_status/
cp check_catalog_status.py lambda_packages/check_status/lambda_function.py
cd lambda_packages/check_status && zip -r ../check_status.zip . && cd ../..

# Package update_catalog_db
mkdir -p lambda_packages/update_db
pip install -r requirements.txt -t lambda_packages/update_db/
cp update_catalog_db.py lambda_packages/update_db/lambda_function.py
cd lambda_packages/update_db && zip -r ../update_db.zip . && cd ../..
```

Upload to AWS Lambda:
- Create `CheckCatalogStatus` function
- Create `UpdateCatalogDB` function (with DB env vars)

### 2. Create Step Function

1. Open AWS Step Functions console
2. Create new state machine
3. Copy content from `state_machine.json`
4. Replace `REGION` and `ACCOUNT_ID` with your values
5. Create with name: `CatalogStatusPollerStateMachine`

### 3. Configure Environment Variable

Add to your backend Lambda environment:
```bash
CATALOG_POLLER_STEP_FUNCTION_ARN=arn:aws:states:REGION:ACCOUNT_ID:stateMachine:CatalogStatusPollerStateMachine
```

### 4. Update IAM Permissions

Backend Lambda needs:
```json
{
  "Effect": "Allow",
  "Action": "states:StartExecution",
  "Resource": "arn:aws:states:*:*:stateMachine:CatalogStatusPollerStateMachine"
}
```

## 📊 What Gets Updated in Database

When catalog is ready, the Step Function updates:

```sql
UPDATE catalog
SET knowledge_base_id = 'kb_name_from_api',
    data_source_id = 'data_source_name_from_api',
    updated_at = CURRENT_TIMESTAMP
WHERE id = local_catalog_id;
```

Previously hardcoded values:
```python
# OLD (in catalog.py:476-477)
knowledge_base_id='WZROVEIVGV',
data_source_id='7E1KNZRZRK'
```

Now dynamically retrieved from external API!

## 🔍 Monitoring & Debugging

### View Execution Status

AWS Console → Step Functions → Executions → Select execution

### CloudWatch Logs

- `/aws/lambda/CheckCatalogStatus`
- `/aws/lambda/UpdateCatalogDB`

### Backend Logs

Look for:
```
TRIGGERING CATALOG STATUS POLLER STEP FUNCTION
Step Function execution started: arn:aws:states:...
```

## 💰 Cost

Per catalog creation: **~$0.008** (less than 1 cent)
- Step Function: ~$0.002
- Lambda executions: ~$0.006

## ⚠️ Important Notes

1. **JWT Token**: The Step Function stores the JWT token in its state. Ensure tokens have sufficient lifetime (50+ minutes) or implement token refresh logic.

2. **VPC Configuration**: `UpdateCatalogDB` Lambda must be in the same VPC as your RDS database.

3. **Timeout**: If external API takes longer than 50 minutes, you can increase max attempts in `state_machine.json` (currently 150).

4. **apply=true**: The backend now sends `apply=true` to the external API, triggering full catalog creation.

## 📚 Documentation

- Complete deployment guide: `catalog_poller/DEPLOYMENT.md`
- Overview: `catalog_poller/README.md`
- This summary: `CATALOG_POLLER_SUMMARY.md`

## ✨ Next Steps

1. Deploy Lambda functions (see DEPLOYMENT.md)
2. Create Step Function state machine
3. Set environment variable in backend
4. Test by creating a catalog
5. Monitor execution in AWS Console

## 🐛 Troubleshooting Quick Tips

**Step Function not triggering?**
- Check `CATALOG_POLLER_STEP_FUNCTION_ARN` environment variable
- Verify IAM permissions

**Database not updating?**
- Check Lambda VPC configuration
- Verify DB credentials in environment variables
- Check security groups (Lambda → RDS)

**Polling times out?**
- Check CloudWatch logs for errors
- Verify external API is accessible
- Increase max attempts if needed

---

For complete details, see the files in `backend/step_functions/catalog_poller/`
