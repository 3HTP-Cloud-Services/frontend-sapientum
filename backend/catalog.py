from botocore.exceptions import ClientError
from aws_utils import (
    list_s3_folder_contents,
    list_s3_files,
    upload_file_to_s3,
    create_s3_folder
)
from activity import create_activity_catalog_log
from db import get_bucket_name
from models import db, Catalog, User, File, Version, Conversation, CatalogPermission, PermissionType, EventType
from flask import session
import traceback
from datetime import datetime
import random
import re
import string

def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"

    size_names = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1

    return f"{size_bytes:.2f} {size_names[i]}"

def sanitize_s3_folder_name(name):
    # Replace spaces and problematic characters with underscores
    # Keep alphanumeric characters, dashes, and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)

    # Ensure the name is not empty
    if not sanitized:
        sanitized = 'catalog_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    # Ensure name doesn't start with special characters that might cause issues
    if sanitized[0] in '-_':
        sanitized = 'c' + sanitized

    return sanitized

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
        from flask import session

        # Get current user
        user_email = session.get('user_email')
        user = User.query.filter_by(email=user_email).first()

        if not user:
            return []

        # If user is admin or catalog editor, return all catalogs
        if user.is_admin or user.is_catalog_editor:
            db_catalogs = Catalog.query.filter_by(is_active=True).all()
        else:
            # For regular users with chat_access, only return catalogs they have permissions for
            if user.chat_access:
                # Get catalog IDs where user has permissions
                user_permissions = CatalogPermission.query.filter_by(user_id=user.id).all()
                catalog_ids = [perm.catalog_id for perm in user_permissions
                              if perm.permission != PermissionType.NOT_ALLOWED]

                if not catalog_ids:
                    return []  # User has no catalog permissions

                db_catalogs = Catalog.query.filter(Catalog.id.in_(catalog_ids), Catalog.is_active==True).all()
            else:
                return []  # User has no chat access

        catalog_list = []

        for catalog in db_catalogs:
            catalog_dict = catalog.to_dict()
            catalog_dict['catalog_name'] = catalog.name

            # Count actual files with active versions in this catalog
            from sqlalchemy import and_
            file_count = db.session.query(File.id)\
                .join(Version, and_(Version.file_id == File.id, Version.active == True))\
                .filter(File.catalog_id == catalog.id)\
                .distinct()\
                .count()

            catalog_dict['document_count'] = file_count
            catalog_list.append(catalog_dict)

        return catalog_list
    except Exception as e:
        print(f"Error getting all catalogs: {e}")
        traceback.print_exc()
        return []

def get_catalog_users(catalog_id):
    print('get_catalog_users:', catalog_id)

    catalog_users = CatalogPermission.query.filter_by(catalog_id=catalog_id).all()
    users = []

    for cu in catalog_users:
        user = User.query.get(cu.user_id)
        if user:
            user_data = user.to_dict()
            user_data['permission'] = cu.permission.value
            users.append(user_data)

    return users

def get_available_users_for_catalog(catalog_id):
    existing_users_query = db.session.query(CatalogPermission.user_id).filter(CatalogPermission.catalog_id == catalog_id)
    existing_user_ids = [user_id for (user_id,) in existing_users_query]

    available_users = User.query.filter(User.is_active == True, ~User.id.in_(existing_user_ids)).all()

    return [user.to_dict() for user in available_users]

def add_user_to_catalog(catalog_id, user_id, permission_value):
    try:
        permission_type = PermissionType(permission_value)
    except ValueError:
        return {"error": f"Valor de permiso inválido: {permission_value}"}, 400

    try:
        existing_permission = CatalogPermission.query.filter_by(
            catalog_id=catalog_id,
            user_id=user_id
        ).first()

        if existing_permission:
            existing_permission.permission = permission_type
        else:
            new_permission = CatalogPermission(
                catalog_id=catalog_id,
                user_id=user_id,
                permission=permission_type
            )
            db.session.add(new_permission)

        db.session.commit()
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"error": f"Error al guardar permisos: {str(e)}"}, 500

def remove_user_from_catalog(catalog_id, user_id):
    try:
        permission = CatalogPermission.query.filter_by(
            catalog_id=catalog_id,
            user_id=user_id
        ).first()

        if not permission:
            return {"error": "Permiso no encontrado"}, 404

        db.session.delete(permission)
        db.session.commit()
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"error": f"Error al eliminar permiso: {str(e)}"}, 500

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

                # Get the active version for this file
                active_version = Version.query.filter_by(file_id=file.id, active=True).first()

                # Make sure field names match what frontend expects
                file_dict['id'] = file_dict.get('id', file.id)

                # Get original version (lowest version number)
                original_version = Version.query.filter_by(file_id=file.id).order_by(Version.version).first()

                # Use active version's filename as the current filename
                if active_version:
                    # Store the original file name
                    file_dict['original_filename'] = original_version.filename if original_version else file.name

                    # Use active version info for display
                    file_dict['name'] = active_version.filename
                    file_dict['version'] = str(active_version.version)
                    file_dict['size'] = format_size(active_version.size)
                    file_dict['active_version_id'] = active_version.id
                else:
                    file_dict['name'] = file_dict.get('name', file.name)
                    file_dict['original_filename'] = file_dict['name']
                    file_dict['version'] = '1.0'
                    file_dict['size'] = file_dict.get('size_formatted', '0 B')

                file_dict['uploadDate'] = file_dict.get('uploaded_at')
                file_dict['description'] = file_dict.get('summary', '')
                file_dict['status'] = file_dict.get('status', 'Published')

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

        # Use the s3Id as the folder path in S3
        # s3Id now contains the path in format "{catalog_type}/{sanitized_s3_name}"
        folder_path = catalog.s3Id  # This already includes catalog_type and sanitized name
        folder_prefix = f"catalog_dir/{folder_path}"
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

        # Use default catalog_type if not provided
        if not catalog_type:
            catalog_type = 's3_folder'

        # Sanitize catalog name for S3 compatibility
        sanitized_s3_name = sanitize_s3_folder_name(catalog_name)

        # Check if catalog_type folder exists in catalog_dir
        catalog_type_folders = list_s3_folder_contents(bucket_name, 'catalog_dir')

        # Create catalog_type folder if it doesn't exist
        if catalog_type not in catalog_type_folders:
            print(f"Creating catalog_type folder: {catalog_type}")
            type_folder_path = create_s3_folder(bucket_name, catalog_type)
            if not type_folder_path:
                print(f"Error creating catalog_type folder: {catalog_type}")
                return None

        # Get a fresh S3 client with assumed role credentials
        from aws_utils import get_client_with_assumed_role
        s3_client = get_client_with_assumed_role('s3')

        # Create the folder path
        folder_path = f"catalog_dir/{catalog_type}/{sanitized_s3_name}/"

        # Create the folder in S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=folder_path,
            Body=''
        )

        # Create a .metadata file inside the folder with catalog details
        import json
        from datetime import datetime

        metadata_content = {
            'type': catalog_type,
            'description': description or f"S3 folder in catalog_dir/{catalog_type} ({catalog_name})",
            'created_at': str(datetime.now()),
            'name': catalog_name
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

        if not folder_path:
            return None

        # Create a database entry for the catalog
        try:
            # Get user ID from session
            user_email = session.get('user_email')
            user = User.query.filter_by(email=user_email).first()
            user_id = user.id if user else None

            # Store the full path (including catalog_type) in the s3Id field
            # This will be used by other functions to locate the folder
            s3_path = f"{catalog_type}/{sanitized_s3_name}"

            new_catalog = Catalog(
                name=catalog_name,  # Use original name for display
                s3Id=s3_path,  # Use path including catalog_type
                description=description or f"S3 folder in catalog_dir/{catalog_type} ({catalog_name})",
                type=catalog_type,
                created_by_id=user_id,
                is_active=True
            )
            db.session.add(new_catalog)
            db.session.commit()
            create_activity_catalog_log(EventType.CATALOG_CREATION, session.get['user_id'], new_catalog.id, 'User ' + session['user_email'] + ' created the catalog ' + catalog_name)

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

        if catalog:
            bucket_name = get_bucket_name()
            if not bucket_name:
                return None

            # Get user ID from session
            user_email = session.get('user_email')
            user = User.query.filter_by(email=user_email).first()
            user_id = user.id if user else None

            # Create a database record for the file
            current_time = datetime.now()
            file_size = len(file_content)

            # First create file record and version record without s3Id
            new_file = File(
                name=file_obj.filename,
                summary=f"Uploaded to {catalog.name}",
                catalog_id=catalog.id,
                created_at=current_time,
                uploaded_at=current_time,
                created_by_id=user_id,
                status="published",
                confidentiality=False,
                size=file_size
            )

            try:
                # Add file to session and flush to get ID
                db.session.add(new_file)
                db.session.flush()

                # Create version record
                version_record = Version(
                    active=True,
                    version=1,
                    s3Id='',  # Placeholder, will update after S3 upload
                    size=file_size,
                    filename=file_obj.filename,
                    uploader_id=user_id,
                    file_id=new_file.id
                )

                # Add version to session and flush to get ID
                db.session.add(version_record)
                db.session.flush()

                # Get file extension from original filename
                file_extension = ""
                if '.' in file_obj.filename:
                    file_extension = file_obj.filename.rsplit('.', 1)[1].lower()

                # Create new filename with catalog_id-file_id-version_id.extension format
                new_filename = f"{catalog.id}-{new_file.id}-{version_record.id}"
                if file_extension:
                    new_filename = f"{new_filename}.{file_extension}"

                # Create a file-like object with the new filename for S3 upload
                from io import BytesIO
                class FileWithCustomName:
                    def __init__(self, content, filename):
                        self.content = content
                        self.filename = filename

                    def read(self):
                        return self.content

                # Create file-like object with new filename
                custom_file_obj = FileWithCustomName(file_content, new_filename)

                # Upload to S3 using the s3Id (sanitized name) from the catalog
                s3_folder_name = catalog.s3Id  # This is already sanitized
                s3_key = upload_file_to_s3(bucket_name, s3_folder_name, custom_file_obj,
                                        file_content, content_type)

                if s3_key:
                    # Update the file and version records with the S3 key
                    new_file.s3Id = s3_key
                    version_record.s3Id = s3_key

                    # Commit the transaction
                    db.session.commit()

                    create_activity_catalog_log(EventType.FILE_UPLOAD, session.get['user_id'], new_file.id, 'User ' + session['user_email'] + ' uploaded the file ' + file_obj.filename)

                    # Return the file dictionary
                    file_dict = new_file.to_dict()

                    # Add frontend-expected fields
                    file_dict['uploadDate'] = file_dict.get('uploaded_at')
                    file_dict['description'] = file_dict.get('summary')
                    if 'size_formatted' not in file_dict:
                        file_dict['size'] = file_dict.get('size_formatted', f"{file_size / 1024:.1f} KB")

                    return file_dict
                else:
                    # S3 upload failed, rollback the transaction
                    db.session.rollback()
                    return None

            except Exception as db_error:
                db.session.rollback()
                import traceback

                upload_date = current_time.isoformat()
                fallback_response = {
                    "id": "",
                    "name": file_obj.filename,
                    "description": f"Uploaded to {catalog.name}",
                    "uploadDate": upload_date,
                    "status": "published",
                    "size": f"{file_size / 1024:.1f} KB",
                    "warning": "File upload failed"
                }
                return fallback_response
        return None
    except Exception as e:
        import traceback
        return None
