from botocore.exceptions import ClientError
from aws_utils import get_dynamodb_table, execute_with_token_refresh
import traceback


import random

def get_catalog_types():
    return [
        {"id": "manual", "name": "manual"},
        {"id": "contract", "name": "contract"}
    ]

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
    
def get_catalog_files(catalog_id):
    mock_documents = [
        {
            "id": 1,
            "name": "Business Requirements Document",
            "description": "Initial requirements for the project scope",
            "uploadDate": "2025-04-15T10:30:00",
            "status": "Published",
            "version": "1.0",
            "size": "4.2 MB"
        },
        {
            "id": 2,
            "name": "Technical Architecture",
            "description": "System architecture diagram and specifications",
            "uploadDate": "2025-04-18T14:15:00",
            "status": "For Review",
            "version": "1.0",
            "size": "2.1 MB"
        },
        {
            "id": 3,
            "name": "User Interface Mockups",
            "description": "Preliminary UI designs for web application",
            "uploadDate": "2025-04-20T09:45:00",
            "status": "Draft",
            "version": "1.0",
            "size": "8.7 MB"
        },
        {
            "id": 4,
            "name": "API Documentation",
            "description": "Endpoints, parameters, and response formats",
            "uploadDate": "2025-04-22T16:20:00",
            "status": "Published",
            "version": "1.0",
            "size": "1.3 MB"
        },
        {
            "id": 5,
            "name": "Data Migration Plan",
            "description": "Strategy for migrating legacy data",
            "uploadDate": "2025-04-25T11:10:00",
            "status": "Deprecated",
            "version": "1.0",
            "size": "3.8 MB"
        }
    ]
    
    return mock_documents