import boto3
from botocore.exceptions import ClientError
import os
import time

# Global variables to store credentials
_credentials = None
_credentials_expiry = 0
_dynamodb_resource = None


def get_dynamodb_resource():
    global _credentials, _credentials_expiry, _dynamodb_resource

    is_lambda = os.environ.get('AWS_EXECUTION_ENV', '').startswith('AWS_Lambda_')

    if is_lambda:
        if _dynamodb_resource is None:
            _dynamodb_resource = boto3.resource('dynamodb', region_name='us-east-1')
        return _dynamodb_resource

    current_time = time.time()

    if _dynamodb_resource and _credentials_expiry > current_time + 60:  # 60 second buffer
        return _dynamodb_resource

    try:
        sts_client = boto3.client('sts', region_name='us-east-1')

        assumed_role = sts_client.assume_role(
            RoleArn='arn:aws:iam::369595298303:role/sapientum_role',
            RoleSessionName='AssumeRoleSession',
            DurationSeconds=3600
        )

        _credentials = assumed_role['Credentials']
        _credentials_expiry = time.mktime(_credentials['Expiration'].timetuple())

        _dynamodb_resource = boto3.resource(
            'dynamodb',
            region_name='us-east-1',
            aws_access_key_id=_credentials['AccessKeyId'],
            aws_secret_access_key=_credentials['SecretAccessKey'],
            aws_session_token=_credentials['SessionToken']
        )

        print(f"Assumed new role, credentials valid until {_credentials['Expiration']}")
        return _dynamodb_resource

    except Exception as e:
        print(f"Error assuming role: {e}")
        return boto3.resource('dynamodb', region_name='us-east-1')


def get_all_catalogs():
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table('sapientum_catalog')

        response = table.scan()
        catalogs = response.get('Items', [])

        # Sort by order if available
        catalogs.sort(key=lambda x: x.get('order', 999))
        return catalogs
    except ClientError as e:
        print(f"Error getting catalogs: {e}")
        return []


def get_catalog_by_id(catalog_id):
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table('sapientum_catalog')

        response = table.get_item(
            Key={
                'id': catalog_id
            }
        )
        return response.get('Item')
    except ClientError as e:
        print(f"Error getting catalog {catalog_id}: {e}")
        return None