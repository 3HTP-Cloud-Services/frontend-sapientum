from botocore.exceptions import ClientError
from aws_utils import get_dynamodb_table, execute_with_token_refresh
import traceback


import random

def get_all_catalogs():
    def operation():
        table = get_dynamodb_table('sapientum_catalogs')
        response = table.scan()
        catalogs = response.get('Items', [])
        
        for catalog in catalogs:
            catalog['document_count'] = random.randint(3, 50)
        
        return catalogs
    
    try:
        return execute_with_token_refresh(operation)
    except ClientError as e:
        print(f"Error getting catalogs: {e}")
        traceback.print_exc()
        return []
    except Exception as e:
        print(f"Unexpected error getting catalogs: {e}")
        traceback.print_exc()
        return []


def get_catalog_by_id(catalog_id):
    def operation():
        table = get_dynamodb_table('sapientum_catalogs')
        response = table.get_item(
            Key={
                'catalog_name': catalog_id
            }
        )
        return response.get('Item')
    
    try:
        return execute_with_token_refresh(operation)
    except ClientError as e:
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