import json
import os
import time
import boto3
import psycopg2
from botocore.exceptions import ClientError

# Global variable to store the S3 bucket name
S3_BUCKET_NAME = None

def get_db_config():
    """Get database configuration from secret manager"""
    global S3_BUCKET_NAME
    
    # Load configuration from config.json
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.json')
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
        secret_arn = config.get('connection_secret')
        database_name = config.get('database_name', 'postgres')
    
    # For development, if we can't connect to AWS Secrets Manager, use local SQLite
    try:
        # Get credentials from AWS Secrets Manager
        secret_data = get_secret(secret_arn)
        
        # Save the bucket name to the global variable
        S3_BUCKET_NAME = secret_data.get('bucket')
        if S3_BUCKET_NAME:
            print(f"Found S3 bucket name: {S3_BUCKET_NAME}")
        else:
            print("Warning: No S3 bucket name found in secrets")
        
        # Build database URI
        host = secret_data.get('host', secret_data.get('endpoint', None))
        port = secret_data.get('port', 5432)
        user = secret_data.get('username', secret_data.get('user', secret_data.get('masterUsername', None)))
        password = secret_data.get('password', secret_data.get('masterUserPassword', None))
        
        # Create SQLAlchemy database URI
        return {
            'SQLALCHEMY_DATABASE_URI': f'postgresql://{user}:{password}@{host}:{port}/{database_name}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'S3_BUCKET_NAME': S3_BUCKET_NAME
        }
    except Exception as e:
        print(f"Warning: Failed to get PostgreSQL credentials: {e}")
        print("Falling back to SQLite for development")
        
        # Use SQLite as a fallback
        sqlite_path = os.path.join(current_dir, 'app.db')
        return {
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{sqlite_path}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'S3_BUCKET_NAME': 'dev-bucket'  # Default bucket name for development
        }

def get_secret(secret_arn):
    """
    Retrieve database connection parameters from AWS Secrets Manager
    
    Expected secret format:
    {
        "username": "your_username",
        "password": "your_password",
        "host": "your_db_host",
        "port": "5432",
        "dbname": "your_database_name"
    }
    """
    print(f"Fetching database credentials from secret ARN: {secret_arn}")
    
    try:
        # Check if we're running locally or in Lambda
        is_lambda = os.environ.get('AWS_EXECUTION_ENV', '').startswith('AWS_Lambda_')
        
        if is_lambda:
            # In Lambda, we already have the necessary IAM role permissions
            session = boto3.session.Session()
            client = boto3.client(
                service_name='secretsmanager',
                region_name='us-east-1'
            )
        else:
            # Running locally, assume the role first
            print("Running locally, assuming role for AWS access")
            
            sts_client = boto3.client('sts', region_name='us-east-1')
            
            response = sts_client.assume_role(
                RoleArn='arn:aws:iam::369595298303:role/sapientum_role',
                RoleSessionName=f'AssumeRoleSession-{int(time.time())}',
                DurationSeconds=3600
            )
            
            # Get temporary credentials
            credentials = response['Credentials']
            
            # Create a Secrets Manager client with the temporary credentials
            client = boto3.client(
                service_name='secretsmanager',
                region_name='us-east-1',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
            
            print("Successfully assumed role for accessing Secrets Manager")
        
        # Get the secret value
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_arn
        )
        
        # Depending on whether the secret is a string or binary, load accordingly
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            secret_data = json.loads(secret)
            print(f"Retrieved secret data with keys: {', '.join(secret_data.keys())}")
            return secret_data
        else:
            raise ValueError("Binary secrets not supported")
    
    except ClientError as e:
        print(f"Error retrieving secret: {e}")
        raise e

def get_bucket_name():
    """Return the S3 bucket name from global variable"""
    global S3_BUCKET_NAME
    return S3_BUCKET_NAME

def test_connection(app):
    """Test the database connection using the app configuration"""
    try:
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        if not db_uri:
            print("Database URI not configured")
            return False
        
        # Check if we're using SQLite
        if db_uri.startswith('sqlite:'):
            print(f"Using SQLite database: {db_uri}")
            # SQLite connection doesn't need to be tested explicitly
            return True
            
        # Extract connection parameters from the URI
        # Format: postgresql://username:password@host:port/dbname
        parts = db_uri.split('://', 1)[1]
        auth, rest = parts.split('@', 1)
        username, password = auth.split(':', 1)
        host_port, dbname = rest.split('/', 1)
        
        # Handle optional port
        if ':' in host_port:
            host, port = host_port.split(':', 1)
            port = int(port)
        else:
            host = host_port
            port = 5432
        
        # Test connection
        print(f"Testing connection to PostgreSQL at {host}:{port}, database: {dbname}")
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=username,
            password=password
        )
        
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        conn.close()
        
        print(f"Successfully connected to PostgreSQL database: {dbname}")
        return True
        
    except Exception as e:
        print(f"Error testing database connection: {e}")
        return False