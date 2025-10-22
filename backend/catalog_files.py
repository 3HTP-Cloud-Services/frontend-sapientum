import traceback
from datetime import datetime
from flask import request, jsonify, send_file
from models import db, File, Version, Catalog
from io import BytesIO

def upload_new_version(file_id, user_id, user_email):
    """Upload a new version of an existing file"""
    print("Starting upload_new_version function")

    try:
        print(f"Fetching file with id {file_id}")
        file = db.session.get(File, file_id)
        if not file:
            print("File not found")
            return jsonify({"error": "File not found"}), 404

        print(f"Fetching active version for file id {file_id}")
        active_version = Version.query.filter_by(file_id=file_id, active=True).first()
        if not active_version:
            print("No active version found for the file")
            return jsonify({"error": "No active version found for this file"}), 404

        if 'file' not in request.files:
            print("No file provided in the request")
            return jsonify({"error": "No file provided"}), 400

        file_obj = request.files['file']
        if file_obj.filename == '':
            print("No file selected")
            return jsonify({"error": "No selected file"}), 400

        file_content = file_obj.read()
        content_type = file_obj.content_type
        file_obj.seek(0)
        print(f"Uploaded file: {file_obj.filename}, size: {len(file_content)} bytes, content type: {content_type}")

        from aws_utils import get_client_with_assumed_role, upload_file_to_s3
        from db import get_bucket_name

        print("Fetching bucket name")
        bucket_name = get_bucket_name()
        if not bucket_name:
            print("S3 bucket configuration not found")
            return jsonify({"error": "S3 bucket configuration not found"}), 500

        catalog = db.session.get(Catalog, file.catalog_id)
        if not catalog:
            return jsonify({"error": "Catalog not found"}), 404

        s3_client = get_client_with_assumed_role('s3')
        # Use the sanitized s3Id from the catalog
        s3_folder_name = catalog.s3Id  # This is already sanitized
        versions_folder = f"catalog_dir/{s3_folder_name}/versions/"

        # Create versions folder if it doesn't exist
        try:
            print(f"Ensuring versions folder exists in S3: {versions_folder}")
            s3_client.put_object(
                Bucket=bucket_name,
                Key=versions_folder,
                Body=''
            )
        except Exception as e:
            traceback.print_exc()
            print(f"Could not create versions folder: {e}")

        # Move the active version to the versions folder
        old_s3_key = active_version.s3Id
        old_file_name = old_s3_key.split('/')[-1]
        new_versions_key = f"{versions_folder}{old_file_name}"

        try:
            print(f"Copying active version from {old_s3_key} to {new_versions_key}")
            s3_client.copy_object(
                Bucket=bucket_name,
                CopySource={'Bucket': bucket_name, 'Key': old_s3_key},
                Key=new_versions_key
            )

            print(f"Deleting old active version {old_s3_key} in S3")
            s3_client.delete_object(
                Bucket=bucket_name,
                Key=old_s3_key
            )

            active_version.s3Id = new_versions_key
            active_version.active = False
            print("Saving old active version in database")
            db.session.flush()
        except Exception as e:
            print(f"Error moving old version to versions folder: {e}")
            return jsonify({"error": f"Error moving old version to versions folder: {str(e)}"}), 500

        print(f"Using current user: {user_email}")

        file_extension = ""
        if '.' in file_obj.filename:
            file_extension = file_obj.filename.rsplit('.', 1)[1].lower()

        new_version_number = active_version.version + 1
        print(f"Creating new version with version number: {new_version_number}")

        class FileWithCustomName:
            def __init__(self, content, filename):
                self.content = content
                self.filename = filename

            def read(self):
                return self.content

        new_version = Version(
            active=True,
            version=new_version_number,
            s3Id='',
            size=len(file_content),
            filename=file_obj.filename,
            uploader_id=user_id,
            file_id=file.id
        )

        print("Adding new version to database session")
        db.session.add(new_version)
        db.session.flush()

        new_filename = f"{catalog.id}-{file.id}-{new_version.id}"
        if file_extension:
            new_filename = f"{new_filename}.{file_extension}"
        print(f"New filename for S3: {new_filename}")

        custom_file_obj = FileWithCustomName(file_content, new_filename)

        print("Uploading new version to S3")
        s3_key = upload_file_to_s3(bucket_name, s3_folder_name, custom_file_obj, file_content, content_type)

        if not s3_key:
            print("Failed to upload new version to S3")
            db.session.rollback()
            return jsonify({"error": "Failed to upload new version to S3"}), 500

        new_version.s3Id = s3_key
        print(f"Uploaded new version with S3 key: {s3_key}")

        file.uploaded_at = datetime.now()
        file.size = len(file_content)

        print("Committing new version to database")
        db.session.commit()

        from catalog import trigger_bedrock_ingestion
        trigger_bedrock_ingestion(catalog)

        print("Successfully uploaded new version")
        return jsonify({
            "success": True,
            "file": file.to_dict(),
            "version": new_version.to_dict()
        })

    except Exception as e:
        print(f"Error during upload_new_version: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"error": f"Error uploading new version: {str(e)}"}), 500

def download_file(file_id):
    """Download the active version of a file"""
    try:
        file = db.session.get(File, file_id)
        if not file:
            return jsonify({"error": "File not found"}), 404

        active_version = Version.query.filter_by(file_id=file_id, active=True).first()
        if not active_version:
            return jsonify({"error": "No active version found for this file"}), 404

        from aws_utils import get_client_with_assumed_role
        from db import get_bucket_name
        from app import sanitize_filename_for_header
        import io

        bucket_name = get_bucket_name()
        if not bucket_name:
            return jsonify({"error": "S3 bucket configuration not found"}), 500

        s3_key = active_version.s3Id
        filename = active_version.filename
        s3_client = get_client_with_assumed_role('s3')

        try:
            s3_response = s3_client.get_object(
                Bucket=bucket_name,
                Key=s3_key
            )

            file_content = s3_response['Body'].read()

            # Use BytesIO and send_file for proper binary handling with Mangum
            file_io = BytesIO(file_content)
            file_io.seek(0)

            response = send_file(
                file_io,
                mimetype=s3_response.get('ContentType', 'application/octet-stream'),
                as_attachment=True,
                download_name=filename
            )

            # Sanitize filename for Content-Disposition header
            sanitized_filename = sanitize_filename_for_header(filename)
            content_disposition = f'attachment; filename="{sanitized_filename}"'
            response.headers['Content-Disposition'] = content_disposition

            print(f"[DOWNLOAD DEBUG] Original filename: {filename}")
            print(f"[DOWNLOAD DEBUG] Sanitized filename: {sanitized_filename}")
            print(f"[DOWNLOAD DEBUG] Content-Disposition set to: {content_disposition}")
            print(f"[DOWNLOAD DEBUG] Response headers: {dict(response.headers)}")

            return response
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": f"Error retrieving file from S3: {str(e)}"}), 500

    except Exception as e:
        print(f"gral exception: {e}")
        traceback.print_exc()
        print(f"gral exception: post trace")
        return jsonify({"error": f"Error downloading file: {str(e)}"}), 500

def update_file(file_id):
    """Update file metadata (description, status, confidentiality)"""
    try:
        file = db.session.get(File, file_id)
        if not file:
            return jsonify({"error": "File not found"}), 404

        data = request.json
        if not data:
            return jsonify({"error": "No se proporcionaron datos"}), 400

        if 'description' in data:
            file.summary = data['description']

        if 'status' in data:
            file.status = data['status']

        if 'confidentiality' in data:
            file.confidentiality = bool(data['confidentiality'])

        db.session.commit()

        return jsonify({
            "success": True,
            "file": file.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error updating file: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Error updating file: {str(e)}"}), 500

def generate_presigned_version_upload_url(file_id, filename, content_type, current_user):
    try:
        file = db.session.get(File, file_id)
        if not file:
            print(f"File not found: {file_id}")
            return None

        active_version = Version.query.filter_by(file_id=file_id, active=True).first()
        if not active_version:
            print(f"No active version found for file {file_id}")
            return None

        catalog = db.session.get(Catalog, file.catalog_id)
        if not catalog:
            print(f"Catalog not found for file {file_id}")
            return None

        from aws_utils import get_client_with_assumed_role
        from db import get_bucket_name

        bucket_name = get_bucket_name()
        if not bucket_name:
            return None

        s3_client = get_client_with_assumed_role('s3')
        s3_folder_name = catalog.s3Id
        versions_folder = f"catalog_dir/{s3_folder_name}/versions/"

        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=versions_folder,
                Body=''
            )
        except Exception as e:
            print(f"Could not create versions folder: {e}")

        old_s3_key = active_version.s3Id
        old_file_name = old_s3_key.split('/')[-1]
        new_versions_key = f"{versions_folder}{old_file_name}"

        try:
            print(f"Copying active version from {old_s3_key} to {new_versions_key}")
            s3_client.copy_object(
                Bucket=bucket_name,
                CopySource={'Bucket': bucket_name, 'Key': old_s3_key},
                Key=new_versions_key
            )

            print(f"Deleting old active version {old_s3_key} in S3")
            s3_client.delete_object(
                Bucket=bucket_name,
                Key=old_s3_key
            )

            active_version.s3Id = new_versions_key
            active_version.active = False
            db.session.flush()
        except Exception as e:
            print(f"Error moving old version to versions folder: {e}")
            db.session.rollback()
            return None

        user_id = current_user.id
        new_version_number = active_version.version + 1

        new_version = Version(
            active=True,
            version=new_version_number,
            s3Id='',
            size=0,
            filename=filename,
            uploader_id=user_id,
            file_id=file.id
        )

        db.session.add(new_version)
        db.session.flush()

        file_extension = ""
        if '.' in filename:
            file_extension = filename.rsplit('.', 1)[1].lower()

        new_filename = f"{catalog.id}-{file.id}-{new_version.id}"
        if file_extension:
            new_filename = f"{new_filename}.{file_extension}"

        s3_key = f"catalog_dir/{s3_folder_name}/documents/{new_filename}"

        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': content_type
            },
            ExpiresIn=900
        )

        db.session.commit()

        return {
            'upload_url': presigned_url,
            's3_key': s3_key,
            'file_id': file.id,
            'version_id': new_version.id,
            'filename': new_filename
        }

    except Exception as e:
        db.session.rollback()
        print(f"Error generating presigned version upload URL: {e}")
        traceback.print_exc()
        return None

def finalize_version_upload(file_id, s3_key, filename, file_size, version_id, current_user):
    try:
        file_record = db.session.get(File, file_id)
        if not file_record:
            print(f"File record not found: {file_id}")
            return None

        version_record = Version.query.filter_by(id=version_id, file_id=file_id).first()
        if not version_record:
            print(f"Version record not found: {version_id}")
            return None

        catalog = db.session.get(Catalog, file_record.catalog_id)
        if not catalog:
            print(f"Catalog not found for file {file_id}")
            return None

        version_record.s3Id = s3_key
        version_record.size = file_size

        file_record.uploaded_at = datetime.now()
        file_record.size = file_size

        db.session.commit()

        from activity import create_activity_catalog_log
        from models import EventType
        create_activity_catalog_log(EventType.FILE_UPLOAD, current_user.email, catalog.id, f'User {current_user.email} uploaded new version of {filename}')

        from catalog import trigger_bedrock_ingestion
        bedrock_response = trigger_bedrock_ingestion(catalog)

        return {
            "success": True,
            "file": file_record.to_dict(),
            "version": version_record.to_dict(),
            "bedrock_ingestion": bedrock_response
        }

    except Exception as e:
        db.session.rollback()
        print(f"Error finalizing version upload: {e}")
        traceback.print_exc()
        return None