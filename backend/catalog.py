from botocore.exceptions import ClientError
from aws_utils import (
    list_s3_folder_contents,
    list_s3_files,
    upload_file_to_s3,
    create_s3_folder
)
from db import get_bucket_name
from models import db, Catalog, User, File
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
    """Get all files for a catalog directly from the database"""
    try:
        # Try to parse as integer for ID lookup
        try:
            catalog_id_int = int(catalog_id)
            catalog = Catalog.query.filter_by(id=catalog_id_int, is_active=True).first()
        except (ValueError, TypeError):
            catalog = None
            
        # If not found by ID, try by s3Id
        if not catalog:
            catalog = Catalog.query.filter_by(s3Id=catalog_id, is_active=True).first()
            catalog_id_int = catalog.id if catalog else None
            
        if not catalog:
            print(f"Catalog not found: {catalog_id}")
            return []
            
        # Query files directly from the database
        files = File.query.filter_by(catalog_id=catalog_id_int).all()
        print(f"Found {len(files)} files in database for catalog ID {catalog_id_int}")
        
        # If we have files in the database, return them
        if files:
            file_dicts = []
            for file in files:
                file_dict = file.to_dict()
                
                # Make sure field names match what frontend expects
                file_dict['id'] = file_dict.get('id', file.id)
                file_dict['name'] = file_dict.get('name', file.name)
                file_dict['uploadDate'] = file_dict.get('uploaded_at')
                file_dict['description'] = file_dict.get('summary', '')
                file_dict['status'] = file_dict.get('status', 'Published')
                file_dict['version'] = file_dict.get('version', '1.0')
                file_dict['size'] = file_dict.get('size_formatted', '0 B')
                
                file_dicts.append(file_dict)
                
            return file_dicts
            
        # If no files in database, try S3 as fallback (older files might not be in DB)
        if catalog.type == 's3_folder':
            s3_files = get_s3_catalog_files(catalog.id)
            if s3_files:
                return s3_files
    except Exception as e:
        print(f"Error getting catalog files: {e}")
        traceback.print_exc()

    # Return empty list if no files found
    return []


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
    """Get files directly from S3 for a catalog - this is used as a fallback only"""
    try:
        # Get catalog from the database
        catalog = Catalog.query.filter_by(id=catalog_id, is_active=True).first()
        
        # If not found by ID, try by s3Id
        if not catalog:
            catalog = Catalog.query.filter_by(s3Id=catalog_id, is_active=True).first()
            
        if not catalog:
            print(f"Catalog not found with id/s3Id {catalog_id}")
            return []
                
        # Get files directly from S3
        bucket_name = get_bucket_name()
        if not bucket_name:
            print("Error: No S3 bucket name available")
            return []
            
        # Use the s3Id as the folder name in S3
        folder_name = catalog.s3Id
        folder_prefix = f"catalog_dir/{folder_name}"
        s3_files = list_s3_files(bucket_name, folder_prefix)
        
        # Do some minimal processing to ensure frontend compatibility
        for file in s3_files:
            # Make sure uploadDate is a string the frontend can parse
            if isinstance(file.get('uploadDate'), datetime):
                file['uploadDate'] = file['uploadDate'].isoformat()
                
        return s3_files
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
    print(
        f"[DEBUG] Starting upload_file_to_catalog for catalog_id={catalog_id}, file={file_obj.filename}, content_type={content_type}")
    try:
        # Get the catalog from the database
        print(f"[DEBUG] Looking up catalog with id={catalog_id}")
        catalog = Catalog.query.filter_by(id=catalog_id, is_active=True).first()
        print(f"[DEBUG] Found catalog by ID: {catalog}")

        # If not found by ID, try using the catalog_id as s3Id
        if not catalog:
            print(f"[DEBUG] Catalog not found by ID, trying s3Id={catalog_id}")
            catalog = Catalog.query.filter_by(s3Id=catalog_id, is_active=True).first()
            print(f"[DEBUG] Found catalog by s3Id: {catalog}")

        if catalog:
            print(f"[DEBUG] Processing valid s3_folder catalog: {catalog.name} (ID: {catalog.id})")
            bucket_name = get_bucket_name()
            print(f"[DEBUG] Got bucket name: {bucket_name}")

            if not bucket_name:
                print("[DEBUG] Error: No S3 bucket name available")
                return None

            # Upload to S3 using the s3Id from the catalog
            s3_folder_name = catalog.s3Id
            print(f"[DEBUG] Uploading to S3 folder: {s3_folder_name}")
            print(f"[DEBUG] File content length: {len(file_content)} bytes")

            s3_key = upload_file_to_s3(bucket_name, s3_folder_name, file_obj,
                                       file_content, content_type)
            print(f"[DEBUG] S3 upload result - key: {s3_key}")

            if s3_key:
                print("[DEBUG] S3 upload successful, creating database record")
                # Get user ID from session
                user_email = session.get('user_email')
                print(f"[DEBUG] User email from session: {user_email}")

                user = User.query.filter_by(email=user_email).first()
                print(f"[DEBUG] Found user: {user}")

                user_id = user.id if user else None
                print(f"[DEBUG] User ID: {user_id}")

                # Create a database record for the file
                current_time = datetime.now()
                file_size = len(file_content)
                print(f"[DEBUG] Current time: {current_time}, File size: {file_size} bytes")

                # Create new file record
                print("[DEBUG] Creating new File record")
                new_file = File(
                    name=file_obj.filename,
                    s3Id=s3_key,
                    summary=f"Uploaded to {catalog.name}",
                    catalog_id=catalog.id,
                    created_at=current_time,
                    uploaded_at=current_time,
                    created_by_id=user_id,
                    version="1.0",
                    status="published",
                    confidentiality=False,
                    size=file_size
                )
                print(f"[DEBUG] New file record created in memory: {new_file}")

                try:
                    print("[DEBUG] Adding file to database session")
                    db.session.add(new_file)
                    print("[DEBUG] Committing to database")
                    db.session.commit()
                    print("[DEBUG] Database commit successful")

                    # Get the dictionary from the model
                    print("[DEBUG] Converting file model to dictionary")
                    file_dict = new_file.to_dict()
                    print(f"[DEBUG] File dictionary: {file_dict}")

                    # Add frontend-expected fields or adjust field names if needed
                    print("[DEBUG] Adding frontend-specific fields")
                    file_dict['uploadDate'] = file_dict.get('uploaded_at')
                    file_dict['description'] = file_dict.get('summary')
                    if 'size_formatted' not in file_dict:
                        file_dict['size'] = file_dict.get('size_formatted', f"{file_size / 1024:.1f} KB")
                    print(f"[DEBUG] Final file dictionary: {file_dict}")

                    print("[DEBUG] Returning successful file upload result")
                    return file_dict
                except Exception as db_error:
                    print(f"[DEBUG] Database error saving file record: {db_error}")
                    import traceback
                    print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                    print("[DEBUG] Rolling back database session")
                    db.session.rollback()

                    # If DB save fails, return basic file info so the upload still "works" for the user
                    print("[DEBUG] Creating fallback response without DB record")
                    upload_date = current_time.isoformat()
                    fallback_response = {
                        "id": s3_key,
                        "name": file_obj.filename,
                        "description": f"Uploaded to {catalog.name}",
                        "uploadDate": upload_date,
                        "status": "published",
                        "version": "1.0",
                        "size": f"{file_size / 1024:.1f} KB",
                        "warning": "File uploaded to S3 but database record creation failed"
                    }
                    print(f"[DEBUG] Returning fallback response: {fallback_response}")
                    return fallback_response
            else:
                print("[DEBUG] S3 upload failed - no s3_key returned")
        else:
            print(f"[DEBUG] Invalid catalog: found={bool(catalog)}, "
                  f"type={catalog.type if catalog else 'N/A'}")

        print("[DEBUG] Returning None - upload failed")
        return None
    except Exception as e:
        print(f"[DEBUG] Unhandled exception in upload_file_to_catalog: {e}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        return None