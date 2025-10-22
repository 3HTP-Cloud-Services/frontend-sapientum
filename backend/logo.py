import traceback
from flask import jsonify, request, send_file
from io import BytesIO
from botocore.exceptions import ClientError

def upload_logo():
    """Upload and resize company logo"""
    try:
        if 'logo' not in request.files:
            return jsonify({"error": "No logo file provided"}), 400

        logo_file = request.files['logo']
        if logo_file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Read file content
        file_content = logo_file.read()

        # Validate it's an image
        try:
            from PIL import Image
            import io

            # Open and validate image
            image = Image.open(io.BytesIO(file_content))

            # Convert to RGB if necessary (handles RGBA, P mode, etc.)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize image maintaining aspect ratio, max 128px on larger side
            width, height = image.size
            max_size = 128

            if width > height:
                new_width = max_size
                new_height = int((height * max_size) / width)
            else:
                new_height = max_size
                new_width = int((width * max_size) / height)

            # Resize image
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert back to bytes
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='PNG', optimize=True)
            resized_content = output_buffer.getvalue()

        except Exception as e:
            return jsonify({"error": f"Invalid image file: {str(e)}"}), 400

        # Upload to S3 root
        from aws_utils import get_client_with_assumed_role
        from db import get_bucket_name

        bucket_name = get_bucket_name()
        if not bucket_name:
            return jsonify({"error": "S3 bucket configuration not found"}), 500

        s3_client = get_client_with_assumed_role('s3')

        try:
            # Upload logo to root of bucket as logo.png
            s3_client.put_object(
                Bucket=bucket_name,
                Key='logo.png',
                Body=resized_content,
                ContentType='image/png'
            )

            return jsonify({
                "success": True,
                "message": "Logo uploaded successfully",
                "size": f"{new_width}x{new_height}"
            })

        except Exception as e:
            return jsonify({"error": f"Failed to upload logo to S3: {str(e)}"}), 500

    except Exception as e:
        print(f"Error uploading logo: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Error uploading logo: {str(e)}"}), 500

def get_logo():
    """Retrieve company logo"""
    try:
        print(f"[LOGO DEBUG] v1 Starting logo retrieval")
        from aws_utils import get_client_with_assumed_role
        from db import get_bucket_name

        bucket_name = get_bucket_name()
        print(f"[LOGO DEBUG] Got bucket name: {bucket_name}")
        if not bucket_name:
            return jsonify({"error": "S3 bucket configuration not found", "location": "get_logo:bucket_check"}), 500

        # Try to get logo from S3 with retry logic
        for attempt in range(2):  # Try twice: initial attempt + 1 retry
            try:
                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Getting S3 client")
                s3_client = get_client_with_assumed_role('s3')

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Calling S3 get_object")
                response = s3_client.get_object(
                    Bucket=bucket_name,
                    Key='logo.png'
                )

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Reading S3 response body")
                logo_content = response['Body'].read()
                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Read {len(logo_content)} bytes")

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Creating BytesIO object for send_file")
                logo_io = BytesIO(logo_content)
                logo_io.seek(0)

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Using send_file for binary response")
                
                response_obj = send_file(
                    logo_io,
                    mimetype='image/png',
                    as_attachment=False,
                    download_name='logo.png'
                )

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Setting cache headers on send_file response")
                # Force no caching - set headers explicitly after response creation
                response_obj.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response_obj.headers['Pragma'] = 'no-cache'
                response_obj.headers['Expires'] = '0'

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Returning send_file response object")
                return response_obj

            except ClientError as e:
                print(f"[LOGO DEBUG] client error except Attempt {attempt + 1}: ClientError occurred")
                error_code = e.response.get('Error', {}).get('Code')
                if error_code == 'NoSuchKey':
                    # Logo doesn't exist, return 404
                    print(f"[LOGO DEBUG] Logo not found in S3")
                    return jsonify({"error": "Logo not found", "location": f"get_logo:s3_not_found:attempt_{attempt+1}"}), 404
                elif error_code in ['InvalidAccessKeyId', 'SignatureDoesNotMatch', 'TokenRefreshRequired', 'ExpiredToken'] and attempt == 0:
                    # Credential-related error on first attempt, force refresh and retry
                    print(f"[LOGO DEBUG] Credential error on logo retrieval: {error_code}, forcing credential refresh")
                    import aws_utils
                    aws_utils._credentials = None  # Force refresh
                    aws_utils._credentials_expiry = 0
                    if not aws_utils.refresh_credentials():
                        return jsonify({"error": "Failed to refresh AWS credentials", "location": f"get_logo:credential_refresh_failed:attempt_{attempt+1}"}), 500
                    continue  # Retry with new credentials
                else:
                    print(f"[LOGO DEBUG] Other ClientError: {str(e)}")
                    return jsonify({"error": f"Error retrieving logo: {str(e)}", "location": f"get_logo:client_error:attempt_{attempt+1}", "error_code": error_code}), 500
            except Exception as e:
                print(f"[LOGO DEBUG] gral except! Attempt {attempt + 1}: General Exception: {str(e)}")
                print(f"[LOGO DEBUG] gral except! Exception type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                if attempt == 0:
                    print(f"[LOGO DEBUG] Retrying after unexpected error: {str(e)}")
                    continue
                else:
                    return jsonify({
                        "error": f"Error retrieving logo: {str(e)}",
                        "location": f"get_logo:general_exception:attempt_{attempt+1}",
                        "exception_type": type(e).__name__,
                        "traceback": traceback.format_exc()
                    }), 500

    except Exception as e:
        print(f"[LOGO DEBUG] Outer exception: {e}")
        print(f"[LOGO DEBUG] Outer exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Error retrieving logo: {str(e)}",
            "location": "get_logo:outer_exception",
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }), 500