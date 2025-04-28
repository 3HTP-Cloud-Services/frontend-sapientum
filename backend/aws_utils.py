import boto3
from botocore.exceptions import ClientError
import os
import time
import traceback
from datetime import datetime

_credentials = None
_credentials_expiry = 0
_dynamodb_resource = None
_last_refresh_attempt = 0


def get_dynamodb_resource():
    global _credentials, _credentials_expiry, _dynamodb_resource, _last_refresh_attempt

    is_lambda = os.environ.get('AWS_EXECUTION_ENV', '').startswith('AWS_Lambda_')

    if is_lambda:
        if _dynamodb_resource is None:
            _dynamodb_resource = boto3.resource('dynamodb', region_name='us-east-1')
        return _dynamodb_resource

    current_time = time.time()
    time_until_expiry = _credentials_expiry - current_time if _credentials_expiry else -1
    
    if (_dynamodb_resource and time_until_expiry > 300):
        return _dynamodb_resource
    
    if time_until_expiry <= 300 and time_until_expiry > 0:
        print(f"Token expiring soon (in {time_until_expiry:.0f} seconds), refreshing...")
    
    try:
        if current_time - _last_refresh_attempt < 5:
            print("Throttling token refresh attempts")
            if _dynamodb_resource:
                return _dynamodb_resource
        
        _last_refresh_attempt = current_time
        sts_client = boto3.client('sts', region_name='us-east-1')

        assumed_role = sts_client.assume_role(
            RoleArn='arn:aws:iam::369595298303:role/sapientum_role',
            RoleSessionName=f'AssumeRoleSession-{int(current_time)}',
            DurationSeconds=3600
        )

        _credentials = assumed_role['Credentials']
        _credentials_expiry = time.mktime(_credentials['Expiration'].timetuple())
        
        expiry_time = datetime.fromtimestamp(_credentials_expiry)
        current_time_dt = datetime.now()
        duration = expiry_time - current_time_dt
        
        _dynamodb_resource = boto3.resource(
            'dynamodb',
            region_name='us-east-1',
            aws_access_key_id=_credentials['AccessKeyId'],
            aws_secret_access_key=_credentials['SecretAccessKey'],
            aws_session_token=_credentials['SessionToken']
        )

        print(f"Assumed new role, credentials valid for {duration.seconds//60} minutes until {expiry_time}")
        return _dynamodb_resource

    except Exception as e:
        print(f"Error assuming role: {e}")
        traceback.print_exc()
        if _dynamodb_resource and time_until_expiry > 0:
            print("Using existing credentials despite refresh error")
            return _dynamodb_resource
        return boto3.resource('dynamodb', region_name='us-east-1')


def get_dynamodb_table(table_name):
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table(table_name)