from botocore.exceptions import ClientError
from aws_utils import (
    list_s3_folder_contents,
    list_s3_files,
    upload_file_to_s3,
)
from db import get_bucket_name
import traceback
from datetime import datetime


import random

def get_catalog_types():
    return [
        {"id": "manual", "name": "manual"},
        {"id": "contract", "name": "contract"},
        {"id": "s3_folder", "name": "S3 Folder"}
    ]

def get_s3_folders():
    try:
        bucket_name = get_bucket_name()
        if not bucket_name:
            print("Error: No S3 bucket name available")
            return []

        # try:
        #     has_metadata = check_s3_metadata(bucket_name)
        #     print('has_metadata', has_metadata)
        #     if not has_metadata:
        #         print('no has_metadata, creating it')
        #         result = create_s3_metadata(bucket_name)
        #         print('created metadata result', result)
        # except Exception as e:
        #     print(f"Metadata check/creation error: {e}")
            
        folders = list_s3_folder_contents(bucket_name, 'catalog_dir')
        print(f"Found {len(folders)} folders in S3 bucket '{bucket_name}/catalog_dir'")
        
        s3_catalogs = []
        for folder in folders:
            if folder == '.metadata':
                continue
                
            s3_catalogs.append({
                'id': folder,
                'catalog_name': folder,
                'description': f"S3 folder in catalog_dir ({folder})",
                'type': 's3_folder',
                'document_count': random.randint(3, 50)
            })
            
        return s3_catalogs
    except Exception as e:
        print(f"Error getting S3 folders: {e}")
        traceback.print_exc()
        return []

def get_all_catalogs():
    s3_catalogs = get_s3_folders()
    return s3_catalogs

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
    # Check if this is an S3 folder catalog
    catalog = get_s3_catalog_by_name(catalog_id)
    if catalog and catalog.get('type') == 's3_folder':
        return get_s3_catalog_files(catalog_id)
    
    # If not an S3 catalog or if error retrieving S3 files, return mock data
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


def get_s3_catalog_by_name(catalog_name):
    """Get a catalog by name from S3 folders"""
    s3_catalogs = get_s3_folders()
    for catalog in s3_catalogs:
        if catalog.get('catalog_name') == catalog_name:
            return catalog
    return None


def get_s3_catalog_files(catalog_folder):
    """Get files for an S3 folder catalog"""
    try:
        bucket_name = get_bucket_name()
        if not bucket_name:
            print("Error: No S3 bucket name available")
            return []
            
        # List files in the catalog folder
        folder_prefix = f"catalog_dir/{catalog_folder}"
        files = list_s3_files(bucket_name, folder_prefix)
        
        return files
    except Exception as e:
        print(f"Error getting S3 catalog files: {e}")
        traceback.print_exc()
        return []


def upload_file_to_catalog(catalog_id, file_obj, file_content, content_type=None):
    """Upload a file to a catalog"""
    try:
        # Check if this is an S3 folder catalog
        catalog = get_s3_catalog_by_name(catalog_id)
        if catalog and catalog.get('type') == 's3_folder':
            bucket_name = get_bucket_name()
            if not bucket_name:
                print("Error: No S3 bucket name available")
                return None
                
            # Upload to S3
            s3_key = upload_file_to_s3(bucket_name, catalog_id, file_obj, file_content, content_type)
            
            if s3_key:
                # Create a file record
                upload_date = datetime.now().isoformat()
                file_record = {
                    "id": s3_key,
                    "name": file_obj.filename,
                    "description": f"Uploaded to {catalog_id}",
                    "uploadDate": upload_date,
                    "status": "Published",
                    "version": "1.0",
                    "size": f"{len(file_content)/1024:.1f} KB"
                }
                return file_record
                
        return None
    except Exception as e:
        print(f"Error uploading file to catalog: {e}")
        traceback.print_exc()
        return None