import boto3
from botocore.exceptions import ClientError
import os
import time
import traceback
from datetime import datetime

# Global variables to store credentials and S3 resource
_credentials = None
_credentials_expiry = 0
_s3_resource = None
_last_refresh_attempt = 0


# This is the only function that should assume the role
def refresh_credentials():
    """
    Assumes the sapientum_role and refreshes temporary credentials.
    This is the ONLY function that should call assume_role.
    """
    global _credentials, _credentials_expiry, _s3_resource, _last_refresh_attempt

    current_time = time.time()

    # Throttle refresh attempts
    if current_time - _last_refresh_attempt < 5:
        print("Throttling token refresh attempts")
        return False

    try:
        _last_refresh_attempt = current_time
        sts_client = boto3.client('sts', region_name='us-east-1')

        # This is the only place where assume_role should be called
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

        # Create S3 resource with the temporary credentials
        _s3_resource = boto3.resource(
            's3',
            region_name='us-east-1',
            aws_access_key_id=_credentials['AccessKeyId'],
            aws_secret_access_key=_credentials['SecretAccessKey'],
            aws_session_token=_credentials['SessionToken']
        )

        print(f"Assumed new role, credentials valid for {duration.seconds // 60} minutes until {expiry_time}")
        return True
    except Exception as e:
        print(f"Error assuming role: {e}")
        traceback.print_exc()
        return False


# This function checks if credentials need refreshing and returns the S3 resource
def get_s3_resource():
    """
    Returns an S3 resource with valid credentials.
    Handles credential refreshing if needed.
    """
    global _credentials, _credentials_expiry, _s3_resource

    # Check if running in Lambda (uses Lambda's execution role instead)
    is_lambda = os.environ.get('AWS_EXECUTION_ENV', '').startswith('AWS_Lambda_')
    if is_lambda:
        if _s3_resource is None:
            _s3_resource = boto3.resource('s3', region_name='us-east-1')
        return _s3_resource

    # Check if credentials are still valid
    current_time = time.time()
    time_until_expiry = _credentials_expiry - current_time if _credentials_expiry else -1

    # If we have valid credentials that aren't about to expire
    if _s3_resource and time_until_expiry > 300:
        return _s3_resource

    # If credentials are about to expire, log it
    if time_until_expiry <= 300 and time_until_expiry > 0:
        print(f"Token expiring soon (in {time_until_expiry:.0f} seconds), refreshing...")

    # Try to refresh credentials
    if not refresh_credentials():
        # If refresh failed but we have valid (though expiring) credentials, use them
        if _s3_resource and time_until_expiry > 0:
            print("Using existing credentials despite refresh error")
            return _s3_resource
        # As a last resort, return default credentials
        return boto3.resource('s3', region_name='us-east-1')

    return _s3_resource


# Helper function to retry operations when tokens expire
def execute_with_token_refresh(operation_func, max_retries=2):
    """
    Executes a function with automatic token refresh on ExpiredToken errors.
    """
    for attempt in range(max_retries):
        try:
            return operation_func()
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if (error_code == 'ExpiredTokenException' or error_code == 'ExpiredToken') and attempt < max_retries - 1:
                print(f"Token expired, retrying... (attempt {attempt + 1}/{max_retries})")
                # Just get a fresh S3 resource - don't call refresh_credentials directly
                get_s3_resource()  # This will refresh if needed
                continue
            raise


# Example S3 operations that should NOT call refresh_credentials directly
def list_s3_folder_contents(bucket_name, prefix=''):
    """List folders in an S3 bucket path"""
    try:
        prefix = prefix.rstrip('/') + '/' if prefix else ''
        # Use get_s3_resource instead of calling refresh_credentials directly
        s3 = get_s3_resource()
        bucket = s3.Bucket(bucket_name)

        result = bucket.meta.client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            Delimiter='/'
        )

        folders = []
        if 'CommonPrefixes' in result:
            for common_prefix in result['CommonPrefixes']:
                folder_path = common_prefix['Prefix']
                folder_name = folder_path.rstrip('/')
                if prefix:
                    folder_name = folder_name.replace(prefix.rstrip('/'), '', 1)
                folder_name = folder_name.lstrip('/')
                folders.append(folder_name)

        return folders
    except Exception as e:
        print(f"Error listing S3 folder contents: {e}")
        traceback.print_exc()
        return []


def list_s3_files(bucket_name, prefix=''):
    """List files in an S3 bucket prefix"""
    try:
        prefix = prefix.rstrip('/') + '/' if prefix else ''
        # Use get_s3_resource which will handle credential refreshing
        s3 = get_s3_resource()
        bucket = s3.Bucket(bucket_name)

        result = bucket.meta.client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )

        files = []
        if 'Contents' in result:
            for item in result['Contents']:
                if item['Key'] == prefix:
                    continue

                key_path = item['Key']
                file_name = key_path.split('/')[-1] if '/' in key_path else key_path

                if not file_name:
                    continue

                size_bytes = item['Size']
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

                file_obj = {
                    "id": key_path,
                    "name": file_name,
                    "description": f"File in {prefix}",
                    "uploadDate": item['LastModified'].isoformat(),
                    "status": "Published",
                    "version": "1.0",
                    "size": size_str
                }

                files.append(file_obj)

        return files
    except Exception as e:
        print(f"Error listing S3 files: {e}")
        traceback.print_exc()
        return []


def create_s3_metadata(bucket_name):
    """Create metadata in S3 bucket"""
    try:
        # Use get_s3_resource which will handle credential refreshing
        s3 = get_s3_resource()
        import json

        metadata_content = {
            'type': 's3_folder',
            'created_at': str(datetime.now()),
            'has_metadata': 'true'
        }

        metadata_key = 'catalog_dir/.metadata'

        s3.Object(bucket_name, metadata_key).put(
            Body=json.dumps(metadata_content),
            ContentType='application/json'
        )

        print(f"Created metadata object in bucket '{bucket_name}'")

        try:
            s3.Object(bucket_name, 'catalog_dir/').put(Body='')
        except Exception as folder_error:
            print(f"Note: Error creating catalog_dir folder marker: {folder_error}")

        return True

    except Exception as e:
        print(f"Error creating S3 metadata: {e}")
        traceback.print_exc()
        return False


def upload_file_to_s3(bucket_name, catalog_folder, file_obj, file_content, content_type=None):
    """Upload a file to S3 bucket"""
    try:
        folder_path = f"catalog_dir/{catalog_folder}/"

        file_key = f"{folder_path}{file_obj.filename}"

        # Use get_s3_resource which will handle credential refreshing
        s3 = get_s3_resource()
        bucket = s3.Bucket(bucket_name)

        if not content_type:
            content_type = 'application/octet-stream'

        bucket.put_object(
            Key=file_key,
            Body=file_content,
            ContentType=content_type
        )

        print(f"Successfully uploaded {file_obj.filename} to {bucket_name}/{file_key}")
        return file_key

    except Exception as e:
        print(f"Error uploading file to S3: {e}")
        traceback.print_exc()
        return None