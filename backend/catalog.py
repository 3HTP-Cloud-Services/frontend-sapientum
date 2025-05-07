from botocore.exceptions import ClientError
from aws_utils import (
    list_s3_folder_contents,
    list_s3_files,
    upload_file_to_s3,
    create_s3_folder
)
from db import get_bucket_name
from models import db, Catalog, User
from flask import session
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

        folders = list_s3_folder_contents(bucket_name, 'catalog_dir')
        print(f"Found {len(folders)} folders in S3 bucket '{bucket_name}/catalog_dir'")
        
        return folders
    except Exception as e:
        print(f"Error getting S3 folders: {e}")
        traceback.print_exc()
        return []

def get_all_catalogs():
    try:
        # Get all active catalogs from the database
        db_catalogs = Catalog.query.filter_by(is_active=True).all()
        
        # Format the catalog data with additional fields
        catalog_list = []
        
        for catalog in db_catalogs:
            catalog_dict = catalog.to_dict()
            # Add frontend-expected fields
            catalog_dict['catalog_name'] = catalog.name
            catalog_dict['document_count'] = random.randint(3, 50)  # Could be replaced with actual count
            catalog_list.append(catalog_dict)
        
        return catalog_list
    except Exception as e:
        print(f"Error getting all catalogs: {e}")
        traceback.print_exc()
        return []

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
    # Try to get the catalog from the database (using both id and s3Id fields)
    try:
        # First try by id (integer)
        try:
            catalog_id_int = int(catalog_id)
            catalog = Catalog.query.filter_by(id=catalog_id_int, is_active=True).first()
        except (ValueError, TypeError):
            catalog = None
            
        # If not found, try by s3Id (string)
        if not catalog:
            catalog = Catalog.query.filter_by(s3Id=catalog_id, is_active=True).first()
            
        if catalog and catalog.type == 's3_folder':
            return get_s3_catalog_files(catalog.id)
    except Exception as e:
        print(f"Error looking up catalog for files: {e}")
        traceback.print_exc()

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
    """Get a catalog by name or s3Id from the database"""
    try:
        # First try to find by s3Id which maps to the folder name
        catalog = Catalog.query.filter_by(s3Id=catalog_name, is_active=True).first()
        
        # If not found, try by name
        if not catalog:
            catalog = Catalog.query.filter_by(name=catalog_name, is_active=True).first()
            
        if catalog:
            catalog_dict = catalog.to_dict()
            catalog_dict['catalog_name'] = catalog.name
            catalog_dict['document_count'] = random.randint(3, 50)
            return catalog_dict
            
        return None
    except Exception as e:
        print(f"Error getting catalog by name: {e}")
        traceback.print_exc()
        return None


def get_s3_catalog_files(catalog_id):
    """Get files for an S3 folder catalog"""
    try:
        bucket_name = get_bucket_name()
        if not bucket_name:
            print("Error: No S3 bucket name available")
            return []
            
        # Get catalog from the database
        catalog = Catalog.query.filter_by(id=catalog_id, is_active=True).first()
        
        # If not found by ID, try by s3Id
        if not catalog:
            catalog = Catalog.query.filter_by(s3Id=catalog_id, is_active=True).first()
            
        if not catalog:
            print(f"Catalog not found with id/s3Id {catalog_id}")
            return []
            
        # Use the s3Id as the folder name in S3
        folder_name = catalog.s3Id
        folder_prefix = f"catalog_dir/{folder_name}"
        files = list_s3_files(bucket_name, folder_prefix)

        return files
    except Exception as e:
        print(f"Error getting S3 catalog files: {e}")
        traceback.print_exc()
        return []


def create_catalog(catalog_name, description=None, catalog_type=None):
    try:
        bucket_name = get_bucket_name()
        if not bucket_name:
            print("Error: No S3 bucket name available")
            return None

        if not catalog_name:
            print("Error: No catalog name provided")
            return None

        # Create the S3 folder
        folder_path = create_s3_folder(bucket_name, catalog_name)
        if not folder_path:
            return None

        # Create a database entry for the catalog
        try:
            # Get user ID from session
            user_email = session.get('user_email')
            user = User.query.filter_by(email=user_email).first()
            user_id = user.id if user else None
            
            new_catalog = Catalog(
                name=catalog_name,
                s3Id=catalog_name,
                description=description or f"S3 folder in catalog_dir ({catalog_name})",
                type=catalog_type or 's3_folder',
                created_by_id=user_id,
                is_active=True
            )
            
            db.session.add(new_catalog)
            db.session.commit()
            
            return new_catalog.to_dict()
        except Exception as db_error:
            print(f"Database error creating catalog: {db_error}")
            traceback.print_exc()
            db.session.rollback()
            return None

    except Exception as e:
        print(f"Error creating catalog: {e}")
        traceback.print_exc()
        return None


def upload_file_to_catalog(catalog_id, file_obj, file_content, content_type=None):
    """Upload a file to a catalog"""
    try:
        # Get the catalog from the database
        catalog = Catalog.query.filter_by(id=catalog_id, is_active=True).first()
        
        # If not found by ID, try using the catalog_id as s3Id
        if not catalog:
            catalog = Catalog.query.filter_by(s3Id=catalog_id, is_active=True).first()
            
        if catalog and catalog.type == 's3_folder':
            bucket_name = get_bucket_name()
            if not bucket_name:
                print("Error: No S3 bucket name available")
                return None

            # Upload to S3 using the s3Id from the catalog
            s3_folder_name = catalog.s3Id
            s3_key = upload_file_to_s3(bucket_name, s3_folder_name, file_obj,
                                       file_content, content_type)

            if s3_key:
                # Create a file record
                upload_date = datetime.now().isoformat()
                file_record = {
                    "id": s3_key,
                    "name": file_obj.filename,
                    "description": f"Uploaded to {catalog.name}",
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