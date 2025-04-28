from botocore.exceptions import ClientError
from aws_utils import get_dynamodb_table
import traceback


import random

def get_all_catalogs():
    max_retries = 2
    for attempt in range(max_retries):
        try:
            table = get_dynamodb_table('sapientum_catalogs')
            response = table.scan()
            catalogs = response.get('Items', [])
            
            for catalog in catalogs:
                catalog['document_count'] = random.randint(3, 50)
            
            return catalogs
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ExpiredToken' and attempt < max_retries - 1:
                print(f"Token expired, retrying... (attempt {attempt+1}/{max_retries})")
                continue
            elif error_code == 'ExpiredToken':
                print(f"Token still expired after {max_retries} attempts: {e}")
                traceback.print_exc()
                return []
            else:
                print(f"Error getting catalogs: {e}")
                traceback.print_exc()
                return []
        except Exception as e:
            print(f"Unexpected error getting catalogs: {e}")
            traceback.print_exc()
            return []


def get_catalog_by_id(catalog_id):
    max_retries = 2
    for attempt in range(max_retries):
        try:
            table = get_dynamodb_table('sapientum_catalogs')
            response = table.get_item(
                Key={
                    'catalog_name': catalog_id
                }
            )
            return response.get('Item')
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ExpiredToken' and attempt < max_retries - 1:
                print(f"Token expired, retrying... (attempt {attempt+1}/{max_retries})")
                continue
            elif error_code == 'ExpiredToken':
                print(f"Token still expired after {max_retries} attempts: {e}")
                traceback.print_exc()
                return None
            else:
                print(f"Error getting catalog {catalog_id}: {e}")
                traceback.print_exc()
                return None
        except Exception as e:
            print(f"Unexpected error getting catalog {catalog_id}: {e}")
            traceback.print_exc()
            return None


def get_catalog_users(catalog_id):
    catalog_users = [
        {
            "id": 1,
            "email": "jprojas@3htp.com",
            "fullName": "Juan Pedro Rojas",
            "role": "lector"
        },
        {
            "id": 2,
            "email": "drisi@3htp.com",
            "fullName": "Dante Risi",
            "role": "editor"
        },
    ]
    
    return catalog_users