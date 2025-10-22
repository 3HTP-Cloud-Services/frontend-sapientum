#!/usr/bin/env python3
import boto3
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db as db_utils
from aws_utils import get_client_with_assumed_role

def setup_s3_cors():
    """Configure CORS on the S3 bucket to allow direct uploads from the frontend"""

    print("Initializing database configuration...")
    db_config = db_utils.get_db_config()
    if not db_config:
        print("Error: Could not get database configuration")
        return False

    bucket_name = db_utils.get_bucket_name()
    if not bucket_name:
        print("Error: Could not get bucket name")
        return False

    print(f"Configuring CORS for bucket: {bucket_name}")

    cors_configuration = {
        'CORSRules': [
            {
                'AllowedOrigins': [
                    'https://sapientum-app.3htp.cloud',
                    'http://localhost:5000',
                    'http://localhost:8080',
                    'http://127.0.0.1:5000',
                    'http://127.0.0.1:8080'
                ],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                'AllowedHeaders': ['*'],
                'ExposeHeaders': [
                    'ETag',
                    'x-amz-request-id',
                    'x-amz-id-2'
                ],
                'MaxAgeSeconds': 3600
            }
        ]
    }

    try:
        s3_client = get_client_with_assumed_role('s3')

        response = s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )

        print("CORS configuration applied successfully!")
        print(f"Response: {response}")

        print("\nVerifying CORS configuration...")
        cors_config = s3_client.get_bucket_cors(Bucket=bucket_name)
        print("Current CORS configuration:")
        print(json.dumps(cors_config['CORSRules'], indent=2))

        return True

    except Exception as e:
        print(f"Error setting up CORS: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = setup_s3_cors()
    if success:
        print("\n✓ S3 CORS configuration completed successfully!")
    else:
        print("\n✗ Failed to configure S3 CORS")
