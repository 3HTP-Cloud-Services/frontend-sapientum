import boto3
from botocore.exceptions import ClientError
import os
import time
import traceback
from datetime import datetime

_credentials = None
_credentials_expiry = 0
_dynamodb_resource = None
_s3_resource = None
_last_refresh_attempt = 0


def refresh_credentials():
    global _credentials, _credentials_expiry, _dynamodb_resource, _s3_resource, _last_refresh_attempt
    
    current_time = time.time()
    
    if current_time - _last_refresh_attempt < 5:
        print("Throttling token refresh attempts")
        return False
    
    try:
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
        
        # Create DynamoDB resource
        _dynamodb_resource = boto3.resource(
            'dynamodb',
            region_name='us-east-1',
            aws_access_key_id=_credentials['AccessKeyId'],
            aws_secret_access_key=_credentials['SecretAccessKey'],
            aws_session_token=_credentials['SessionToken']
        )
        
        # Create S3 resource
        _s3_resource = boto3.resource(
            's3',
            region_name='us-east-1',
            aws_access_key_id=_credentials['AccessKeyId'],
            aws_secret_access_key=_credentials['SecretAccessKey'],
            aws_session_token=_credentials['SessionToken']
        )

        print(f"Assumed new role, credentials valid for {duration.seconds//60} minutes until {expiry_time}")
        return True
    except Exception as e:
        print(f"Error assuming role: {e}")
        traceback.print_exc()
        return False


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
    
    if not refresh_credentials():
        if _dynamodb_resource and time_until_expiry > 0:
            print("Using existing credentials despite refresh error")
            return _dynamodb_resource
        return boto3.resource('dynamodb', region_name='us-east-1')
    
    return _dynamodb_resource


def get_dynamodb_table(table_name):
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table(table_name)


def get_s3_resource():
    global _credentials, _credentials_expiry, _s3_resource, _last_refresh_attempt

    is_lambda = os.environ.get('AWS_EXECUTION_ENV', '').startswith('AWS_Lambda_')

    if is_lambda:
        if _s3_resource is None:
            _s3_resource = boto3.resource('s3', region_name='us-east-1')
        return _s3_resource

    current_time = time.time()
    time_until_expiry = _credentials_expiry - current_time if _credentials_expiry else -1
    
    if (_s3_resource and time_until_expiry > 300):
        return _s3_resource
    
    if time_until_expiry <= 300 and time_until_expiry > 0:
        print(f"Token expiring soon (in {time_until_expiry:.0f} seconds), refreshing...")
    
    if not refresh_credentials():
        if _s3_resource and time_until_expiry > 0:
            print("Using existing credentials despite refresh error")
            return _s3_resource
        return boto3.resource('s3', region_name='us-east-1')
    
    return _s3_resource


def execute_with_token_refresh(operation_func, max_retries=2):
    """Execute a DynamoDB operation with auto token refresh if expired"""
    for attempt in range(max_retries):
        try:
            return operation_func()
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if (error_code == 'ExpiredTokenException' or error_code == 'ExpiredToken') and attempt < max_retries - 1:
                print(f"Token expired, refreshing and retrying... (attempt {attempt+1}/{max_retries})")
                if refresh_credentials():
                    continue
                else:
                    print("Failed to refresh credentials")
            raise


def list_s3_folder_contents(bucket_name, prefix=''):
    """
    List all objects within a specific S3 bucket prefix (folder)
    Returns a list of folder names (common prefixes) under the given prefix
    """
    try:
        prefix = prefix.rstrip('/') + '/' if prefix else ''
        s3 = get_s3_resource()
        bucket = s3.Bucket(bucket_name)
        
        # Use the list_objects_v2 method with delimiter to get folder-like structure
        result = bucket.meta.client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            Delimiter='/'
        )
        
        # Extract folder names from CommonPrefixes
        folders = []
        if 'CommonPrefixes' in result:
            for common_prefix in result['CommonPrefixes']:
                # Extract just the folder name without the full path
                folder_path = common_prefix['Prefix']
                folder_name = folder_path.rstrip('/')
                if prefix:
                    # Remove the prefix to get just the folder name
                    folder_name = folder_name.replace(prefix.rstrip('/'), '', 1)
                # Remove any leading slash if present after replacing the prefix
                folder_name = folder_name.lstrip('/')
                folders.append(folder_name)
        
        return folders
    except Exception as e:
        print(f"Error listing S3 folder contents: {e}")
        traceback.print_exc()
        return []


def list_s3_files(bucket_name, prefix=''):
    """
    List all files within a specific S3 bucket prefix (folder)
    Returns a list of file objects under the given prefix
    """
    try:
        prefix = prefix.rstrip('/') + '/' if prefix else ''
        s3 = get_s3_resource()
        bucket = s3.Bucket(bucket_name)
        
        # Get objects in the folder
        result = bucket.meta.client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )
        
        files = []
        if 'Contents' in result:
            for item in result['Contents']:
                # Skip the folder itself (often represented as a 0-byte object)
                if item['Key'] == prefix:
                    continue
                    
                # Get just the filename portion
                key_path = item['Key']
                file_name = key_path.split('/')[-1] if '/' in key_path else key_path
                
                # Skip empty folder markers
                if not file_name:
                    continue
                    
                # Format the file size
                size_bytes = item['Size']
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes/1024:.1f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    size_str = f"{size_bytes/(1024*1024):.1f} MB"
                else:
                    size_str = f"{size_bytes/(1024*1024*1024):.1f} GB"
                    
                # Create a file object similar to the mock files in catalog.py
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


def upload_file_to_s3(bucket_name, catalog_folder, file_obj, file_content, content_type=None):
    """
    Upload a file to a specific folder in the S3 bucket
    Returns the S3 object key if successful, None otherwise
    """
    try:
        # Normalize the catalog folder path
        folder_path = f"catalog_dir/{catalog_folder}/"
        
        # Create the full S3 key
        file_key = f"{folder_path}{file_obj.filename}"
        
        # Get the S3 client
        s3 = get_s3_resource()
        bucket = s3.Bucket(bucket_name)
        
        # Set default content type if not provided
        if not content_type:
            content_type = 'application/octet-stream'
            
        # Upload the file with extra args for content type
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