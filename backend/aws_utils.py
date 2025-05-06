import boto3
from botocore.exceptions import ClientError
import os
import time
import traceback
from datetime import datetime

# Global variables
_credentials = None
_credentials_expiry = 0
_last_refresh_attempt = 0


def refresh_credentials():
    """
    Assumes the sapientum_role and refreshes temporary credentials.
    This is the ONLY function that should call assume_role.
    """
    global _credentials, _credentials_expiry, _last_refresh_attempt

    current_time = time.time()

    # Throttle refresh attempts
    if current_time - _last_refresh_attempt < 5:
        print("Throttling token refresh attempts")
        return False

    try:
        _last_refresh_attempt = current_time

        print("Creating a fresh STS client...")
        # Create a fresh STS client - do not reuse any existing client
        sts_client = boto3.client('sts', region_name='us-east-1')

        print("Attempting to assume role: sapientum_role")
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

        print(
            f"Successfully assumed role, credentials valid for {duration.seconds // 60} minutes until {expiry_time}")
        return True
    except Exception as e:
        print(f"Error assuming role: {e}")
        traceback.print_exc()
        return False


def get_client_with_assumed_role(service_name, region_name='us-east-1'):
    """
    Create a boto3 client for the specified service using assumed role credentials.
    Each call creates a fresh client with the current credentials.
    """
    global _credentials, _credentials_expiry

    # Check if credentials are still valid
    current_time = time.time()
    time_until_expiry = _credentials_expiry - current_time if _credentials_expiry else -1

    # If we have no credentials or they're expired or about to expire, refresh
    if _credentials is None or time_until_expiry <= 300:
        # If credentials are about to expire, log it
        if _credentials is not None and time_until_expiry <= 300 and time_until_expiry > 0:
            print(f"Token expiring soon (in {time_until_expiry:.0f} seconds), refreshing...")

        # Force refresh credentials
        if not refresh_credentials():
            print("FAILED to refresh credentials!")
            raise Exception("Failed to assume role, cannot proceed with AWS operations")

    # Create a fresh client with the current assumed role credentials
    print(f"Creating {service_name} client with assumed role credentials")
    return boto3.client(
        service_name,
        region_name=region_name,
        aws_access_key_id=_credentials['AccessKeyId'],
        aws_secret_access_key=_credentials['SecretAccessKey'],
        aws_session_token=_credentials['SessionToken']
    )


def list_s3_folder_contents(bucket_name, prefix=''):
    """List folders in an S3 bucket path using direct S3 client from assumed role"""
    try:
        prefix = prefix.rstrip('/') + '/' if prefix else ''

        # Get a fresh S3 client with assumed role credentials
        s3_client = get_client_with_assumed_role('s3')

        print(f"Listing objects in bucket: {bucket_name}, prefix: {prefix}")

        # Use the client directly instead of through a resource
        result = s3_client.list_objects_v2(
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
    """List files in an S3 bucket prefix using direct S3 client from assumed role"""
    try:
        prefix = prefix.rstrip('/') + '/' if prefix else ''

        # Get a fresh S3 client with assumed role credentials
        s3_client = get_client_with_assumed_role('s3')

        # Use the client directly
        result = s3_client.list_objects_v2(
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
    """Create metadata in S3 bucket using direct S3 client from assumed role"""
    try:
        # Get a fresh S3 client with assumed role credentials
        s3_client = get_client_with_assumed_role('s3')
        import json

        metadata_content = {
            'type': 's3_folder',
            'created_at': str(datetime.now()),
            'has_metadata': 'true'
        }

        metadata_key = 'catalog_dir/.metadata'

        s3_client.put_object(
            Bucket=bucket_name,
            Key=metadata_key,
            Body=json.dumps(metadata_content),
            ContentType='application/json'
        )

        print(f"Created metadata object in bucket '{bucket_name}'")

        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key='catalog_dir/',
                Body=''
            )
        except Exception as folder_error:
            print(f"Note: Error creating catalog_dir folder marker: {folder_error}")

        return True
    except Exception as e:
        print(f"Error creating S3 metadata: {e}")
        traceback.print_exc()
        return False


def create_s3_folder(bucket_name, folder_name):
    """Create a folder in S3 bucket using direct S3 client from assumed role"""
    try:
        # Get a fresh S3 client with assumed role credentials
        s3_client = get_client_with_assumed_role('s3')

        folder_path = f"catalog_dir/{folder_name}/"

        s3_client.put_object(
            Bucket=bucket_name,
            Key=folder_path,
            Body=''
        )

        print(f"Successfully created folder {folder_path} in bucket {bucket_name}")
        return folder_path
    except Exception as e:
        print(f"Error creating S3 folder: {e}")
        traceback.print_exc()
        return None


def upload_file_to_s3(bucket_name, catalog_folder, file_obj, file_content, content_type=None):
    """Upload a file to S3 bucket using direct S3 client from assumed role"""
    try:
        # Get a fresh S3 client with assumed role credentials
        s3_client = get_client_with_assumed_role('s3')

        folder_path = f"catalog_dir/{catalog_folder}/"
        file_key = f"{folder_path}{file_obj.filename}"

        if not content_type:
            content_type = 'application/octet-stream'

        s3_client.put_object(
            Bucket=bucket_name,
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