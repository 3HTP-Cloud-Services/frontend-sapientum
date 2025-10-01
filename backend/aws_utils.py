import boto3
from botocore.exceptions import ClientError
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import os
import time
import traceback
import json
import requests
from datetime import datetime

# Global variables
_credentials = None
_credentials_expiry = 0
_last_refresh_attempt = 0
_using_instance_profile = False

# Load config values
def get_config_value(key, default=None):
    """Load a value from config.json"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.json')
    try:
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            return config.get(key, default)
    except Exception as e:
        print(f"Error loading config value {key}: {e}")
        return default

def get_aws_role_arn():
    """Load AWS Role ARN from config.json"""
    return get_config_value('aws_role_arn')

def get_lambda_url():
    """Load Lambda URL from config.json"""
    return get_config_value('lambda_url', 'https://lambda.us-east-1.amazonaws.com/2015-03-31/functions/my-function/invocations')

def get_agent_id():
    """Load Agent ID from config.json"""
    return get_config_value('agent_id')

def get_agent_alias_id():
    """Load Agent Alias ID from config.json"""
    return get_config_value('agent_alias_id')


def refresh_credentials():
    """
    Refreshes temporary credentials with single retry.
    If running on EC2, uses instance profile credentials.
    If running locally, assumes the configured role.
    This is the ONLY function that should call assume_role.
    """
    global _credentials, _credentials_expiry, _last_refresh_attempt, _using_instance_profile

    current_time = time.time()

    # Throttle refresh attempts
    if current_time - _last_refresh_attempt < 5:
        print("Throttling token refresh attempts")
        return False

    for attempt in range(2):  # Try twice: initial attempt + 1 retry
        try:
            _last_refresh_attempt = current_time

            # Check if running on AWS Lambda
            is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None

            if is_lambda:
                print("Running on AWS Lambda, using Lambda execution role credentials")
                _using_instance_profile = True

                # When using Lambda execution role, we don't need to store credentials
                # as boto3 will automatically use the Lambda execution role
                _credentials = {}
                _credentials_expiry = current_time + 3600  # Set a dummy expiry time
                return True
            else:
                # Running locally, assume a role
                _using_instance_profile = False

                # Get the AWS role ARN from config
                role_arn = get_aws_role_arn()
                if not role_arn:
                    print("Error: AWS Role ARN not found in config")
                    return False

                print(f"Creating a fresh STS client... (attempt {attempt + 1})")
                # Create a fresh STS client - do not reuse any existing client
                sts_client = boto3.client('sts', region_name='us-east-1')

                print(f"Attempting to assume role: {role_arn}")
                # This is the only place where assume_role should be called
                assumed_role = sts_client.assume_role(
                    RoleArn=role_arn,
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
            print(f"Error assuming role (attempt {attempt + 1}): {e}")
            if attempt == 0:  # Only print retry message on first failure
                print("Retrying credential refresh...")
            else:
                traceback.print_exc()

    return False


def get_client_with_assumed_role(service_name, region_name='us-east-1'):
    """
    Create a boto3 client for the specified service using:
    - Instance profile credentials when on EC2
    - Assumed role credentials when running locally
    Only refreshes credentials if they don't exist or are expired.
    """
    global _credentials, _credentials_expiry, _using_instance_profile

    # Check if we need to initialize credentials
    current_time = time.time()
    credentials_expired = False

    if _credentials is None:
        print("No credentials cached, need to get initial credentials")
        credentials_expired = True
    elif _credentials_expiry and current_time >= _credentials_expiry:
        print(f"Credentials expired (expired at {datetime.fromtimestamp(_credentials_expiry)}), need to refresh")
        credentials_expired = True
    elif _credentials_expiry:
        time_until_expiry = _credentials_expiry - current_time
        print(f"Using cached credentials, valid for {time_until_expiry:.0f} more seconds")

    # Only refresh if credentials are missing or expired
    if credentials_expired:
        if not refresh_credentials():
            print("FAILED to refresh credentials!")
            raise Exception("Failed to get credentials, cannot proceed with AWS operations")

    # If using Lambda execution role, just create client without explicit credentials
    if _using_instance_profile:
        print(f"Creating {service_name} client with Lambda execution role credentials")
        return boto3.client(
            service_name,
            region_name=region_name
        )
    else:
        # Create a fresh client with assumed role credentials
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

                # Skip .metadata files when listing regular files
                if file_name == '.metadata':
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


def get_s3_folder_metadata(bucket_name, folder_name):
    """Get metadata for a specific S3 folder"""
    try:
        # Get a fresh S3 client with assumed role credentials
        s3_client = get_client_with_assumed_role('s3')
        import json

        folder_path = f"catalog_dir/{folder_name}/"
        metadata_key = f"{folder_path}.metadata"

        try:
            response = s3_client.get_object(
                Bucket=bucket_name,
                Key=metadata_key
            )

            metadata_content = json.loads(response['Body'].read().decode('utf-8'))
            return metadata_content
        except Exception as e:
            print(f"Error reading metadata for folder {folder_name}: {e}")
            return None
    except Exception as e:
        print(f"Error getting S3 folder metadata: {e}")
        traceback.print_exc()
        return None

def create_s3_folder(bucket_name, folder_name, description=None, catalog_type=None):
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

        # Create a .metadata file inside the folder with catalog details
        import json

        metadata_content = {
            'type': catalog_type or 'General',
            'description': description or f"S3 folder in catalog_dir ({folder_name})",
            'created_at': str(datetime.now()),
            'name': folder_name
        }

        metadata_key = f"{folder_path}.metadata"

        s3_client.put_object(
            Bucket=bucket_name,
            Key=metadata_key,
            Body=json.dumps(metadata_content),
            ContentType='application/json'
        )

        print(f"Successfully created folder {folder_path} in bucket {bucket_name}")
        print(f"Added metadata file {metadata_key} in bucket {bucket_name}")
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

def invoke_lambda_with_sigv4_v2(url, body=None):
    session = boto3.Session()
    base_credentials = session.get_credentials()

    # Create credentials without token (simulate local behavior)
    from botocore.credentials import Credentials
    credentials = Credentials(
        access_key=base_credentials.access_key,
        secret_key=base_credentials.secret_key,
        token=None  # Explicitly set to None
    )

    region = 'us-east-1'

    headers = {
        'Content-Type': 'application/json',
        'Host': url.split('/')[2]
    }

    data = json.dumps(body) if body else ''

    request = AWSRequest(
        method='POST',
        url=url,
        data=data,
        headers=headers
    )

    SigV4Auth(credentials, 'lambda', region).add_auth(request)
    print(f"calling sig v4: credentials {credentials} region {region} headers: {request.headers}")
    response = requests.post(
        url,
        headers=dict(request.headers),
        data=data
    )

    print(f"Status: {response.status_code}")
    return response.json() if response.status_code == 200 else response.text
import boto3
import json
import traceback
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError, ConnectTimeoutError

def call_backend_lambda(payload, timeout_seconds=300):
    """
    Call backend Lambda with enhanced error handling and configurable timeout.

    Args:
        payload: The payload to send to the Lambda function
        timeout_seconds: Maximum time to wait for response (default: 5 minutes)

    Returns:
        Parsed response or None if error
    """
    try:
        # Configure boto3 client with extended timeouts (no retries)
        config = Config(
            region_name='us-east-1',
            retries={
                'max_attempts': 0  # No retries
            },
            read_timeout=timeout_seconds,  # How long to wait for response
            connect_timeout=60,            # How long to wait for connection
            max_pool_connections=50
        )

        lambda_client = boto3.client('lambda', config=config)

        print(f"Invoking Lambda with payload size: {len(json.dumps(payload))} bytes")
        print(f"Timeout configured for: {timeout_seconds} seconds")

        start_time = time.time()

        response = lambda_client.invoke(
            FunctionName='sapientum-backend-agent-lambda',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        invoke_time = time.time() - start_time
        print(f"Lambda invocation completed in {invoke_time:.2f} seconds")

        # Check for Lambda execution errors
        if 'FunctionError' in response:
            print(f"Lambda function error: {response['FunctionError']}")
            error_payload = response['Payload'].read().decode('utf-8')
            print(f"Error details: {error_payload}")
            return None

        if response['StatusCode'] >= 400:
            print(f"Error invoking Lambda: HTTP {response['StatusCode']}")
            print(f"Response: {response.get('Payload', 'No payload')}")
            return None

        # Read and parse the response
        payload_bytes = response['Payload'].read()
        response_size = len(payload_bytes)
        print(f"Received response of {response_size} bytes")

        try:
            parsed_response = json.loads(payload_bytes.decode('utf-8'))
            print(f"call_backend_lambda parsed response type: {type(parsed_response)}")

            # Handle case where Lambda returns a response with statusCode and body
            if isinstance(parsed_response, dict) and 'body' in parsed_response:
                try:
                    # Try to parse the body as JSON
                    body_content = json.loads(parsed_response['body'])
                    print(f"call_backend_lambda extracted body type: {type(body_content)}")
                    return body_content
                except (json.JSONDecodeError, TypeError) as json_error:
                    # If body is not JSON, return the raw body
                    print(f"Body is not JSON, returning raw: {type(parsed_response['body'])}")
                    return parsed_response['body']

            return parsed_response

        except ValueError as parse_error:
            decoded_response = payload_bytes.decode('utf-8')
            print(f"Failed to parse JSON response: {parse_error}")
            print(f"call_backend_lambda raw response: {decoded_response[:500]}...")  # Truncate long responses
            return decoded_response

    except (ConnectTimeoutError, EndpointConnectionError) as conn_error:
        print(f"[ERROR] Connection error when invoking Lambda: {conn_error}")
        print(f"[ERROR] Connection error type: {type(conn_error).__name__}")
        print("[ERROR] This usually indicates network connectivity issues or Lambda cold start delays")
        return {"error": "Connection failed", "message": "Unable to connect to backend service. Please try again later."}

    except ReadTimeoutError as timeout_error:
        print(f"[ERROR] Timeout error when invoking Lambda: {timeout_error}")
        print(f"[ERROR] Lambda execution exceeded {timeout_seconds} seconds timeout")
        print("[ERROR] Consider increasing timeout or optimizing the target Lambda function")
        return {"error": "Timeout", "message": "Backend service is taking too long to respond. Please try again later."}

    except ClientError as client_error:
        error_code = client_error.response['Error']['Code']
        error_message = client_error.response['Error']['Message']
        print(f"[ERROR] AWS Client error ({error_code}): {error_message}")

        if error_code == 'TooManyRequestsException':
            print("[ERROR] Lambda is being throttled - too many concurrent executions")
            return {"error": "Service busy", "message": "Backend service is currently busy. Please try again in a moment."}
        elif error_code == 'ServiceException':
            print("[ERROR] AWS Lambda service error - temporary issue")
            return {"error": "Service error", "message": "Backend service is temporarily unavailable. Please try again later."}
        elif error_code == 'ResourceNotFoundException':
            print("[ERROR] Lambda function not found - check function name")
            return {"error": "Service error", "message": "Backend service configuration error. Please contact support."}

        return {"error": "Service error", "message": "Backend service encountered an error. Please try again later."}

    except Exception as e:
        print(f"[ERROR] Unexpected error invoking Lambda: {type(e).__name__}: {e}")
        traceback.print_exc()
        return {"error": "Unexpected error", "message": "An unexpected error occurred. Please try again later."}

# Usage examples:
# Synchronous with default 5-minute timeout
# result = call_backend_lambda(your_payload)

# Synchronous with custom 10-minute timeout
# result = call_backend_lambda(your_payload, timeout_seconds=600)

def invoke_lambda_with_sigv4(url, method='GET', region='us-east-1', service='lambda', body=None, headers=None):
    """
    Invoke an AWS Lambda function or API using SigV4 authentication.

    Args:
        url (str): The URL to send the request to
        method (str): HTTP method (GET, POST, etc.)
        region (str): AWS region
        service (str): AWS service (lambda, execute-api, etc.)
        body (dict, optional): Request body to be sent as JSON
        headers (dict, optional): Additional headers to include in the request

    Returns:
        dict: The response from the Lambda function or API
    """
    try:
        print(f"\n[AWS_UTILS] invoke_lambda_with_sigv4 called")
        print(f"[AWS_UTILS] URL: {url}")
        print(f"[AWS_UTILS] Method: {method}")
        print(f"[AWS_UTILS] Region: {region}")
        print(f"[AWS_UTILS] Service: {service}")
        print(f"[AWS_UTILS] Body present: {body is not None}")
        if body:
            print(f"[AWS_UTILS] Body keys: {list(body.keys()) if isinstance(body, dict) else 'not a dict'}")

        print(f"\n[AWS_UTILS] Getting AWS credentials...")
        session = boto3.Session()
        credentials = session.get_credentials()

        global _credentials, _using_instance_profile
        if not _using_instance_profile and _credentials:
            print(f"[AWS_UTILS] Using assumed role credentials")
            from botocore.credentials import Credentials
            credentials = Credentials(
                access_key=_credentials['AccessKeyId'],
                secret_key=_credentials['SecretAccessKey'],
                token=_credentials['SessionToken']
            )
        else:
            print(f"[AWS_UTILS] Using instance profile/Lambda execution role credentials")

        print(f"[AWS_UTILS] ✓ Credentials obtained")

        print(f"\n[AWS_UTILS] Preparing request headers...")
        request_headers = {
            'Host': url.split('/')[2],
            'Content-Type': 'application/json'
        }
        if headers:
            request_headers.update(headers)
        print(f"[AWS_UTILS] Headers: {request_headers}")

        print(f"\n[AWS_UTILS] Creating AWS request...")
        request_body = json.dumps(body) if body else ''
        if body:
            print(f"[AWS_UTILS] Request body length: {len(request_body)} characters")

        aws_request = AWSRequest(
            method=method,
            url=url,
            data=request_body if body else None,
            headers=request_headers
        )
        print(f"[AWS_UTILS] ✓ AWS request created")

        print(f"\n[AWS_UTILS] Signing request with SigV4...")
        SigV4Auth(credentials, service, region).add_auth(aws_request)
        print(f"[AWS_UTILS] ✓ Request signed")
        print(f"[AWS_UTILS] Signed headers: {list(aws_request.headers.keys())}")

        request_kwargs = {
            'method': method,
            'url': url,
            'headers': dict(aws_request.headers)
        }

        if body:
            request_kwargs['json'] = body

        print(f"\n[AWS_UTILS] Sending HTTP request to Lambda URL...")
        response = requests.request(**request_kwargs)
        print(f"[AWS_UTILS] ✓ HTTP request completed")
        print(f"[AWS_UTILS] Response status code: {response.status_code}")
        print(f"[AWS_UTILS] Response headers: {dict(response.headers)}")

        if response.status_code >= 400:
            print(f"[AWS_UTILS] ✗ ERROR: HTTP {response.status_code}")
            print(f"[AWS_UTILS] Response body: {response.text[:1000]}")
            return None

        print(f"[AWS_UTILS] ✓ Request successful (HTTP {response.status_code})")

        print(f"\n[AWS_UTILS] Parsing response...")
        try:
            parsed_response = response.json()
            print(f"[AWS_UTILS] ✓ Response parsed as JSON")
            if isinstance(parsed_response, dict):
                print(f"[AWS_UTILS] Response keys: {list(parsed_response.keys())}")
            return parsed_response
        except ValueError as json_error:
            print(f"[AWS_UTILS] ✗ Failed to parse response as JSON: {json_error}")
            print(f"[AWS_UTILS] Returning raw text response")
            return response.text

    except Exception as e:
        print(f"[AWS_UTILS] ✗ EXCEPTION in invoke_lambda_with_sigv4")
        print(f"[AWS_UTILS] Error type: {type(e).__name__}")
        print(f"[AWS_UTILS] Error message: {str(e)}")
        traceback.print_exc()
        return None
