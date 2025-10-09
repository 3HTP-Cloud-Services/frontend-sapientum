"""
Lambda function to check catalog status via external API
This function is called by the Step Function to poll the catalog status
"""
import json
import os
import requests


def lambda_handler(event, context):
    """
    Check the catalog status by calling the external API

    Input event should contain:
    - catalog_name: The name of the catalog to check
    - jwt_token: JWT token for authentication
    - local_catalog_id: The ID of the catalog in the local database
    - attempt_count: Current attempt number (for tracking)

    Returns:
    - success: Whether the API call succeeded
    - catalog_ready: Whether kb_name and data_source_name are valid
    - kb_name: The knowledge base name (if available)
    - data_source_name: The data source name (if available)
    - catalog_data: Full catalog data from API
    - attempt_count: Updated attempt count
    """

    print(f"[CHECK_CATALOG_STATUS] Starting - Event: {json.dumps(event)}")

    # Extract inputs from event
    catalog_name = event.get('catalog_name')
    jwt_token = event.get('jwt_token')
    local_catalog_id = event.get('local_catalog_id')
    attempt_count = event.get('attempt_count', 1)

    if not catalog_name:
        print("[ERROR] Missing catalog_name in event")
        return {
            'success': False,
            'error': 'Missing catalog_name',
            'catalog_ready': False,
            'attempt_count': attempt_count
        }

    # Prepare API request
    base_url = "https://yx8b0cx4za.execute-api.us-east-1.amazonaws.com"
    endpoint = f"{base_url}/api/v1/catalogs/{catalog_name}"

    headers = {
        "Content-Type": "application/json"
    }

    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"

    print(f"[CHECK_CATALOG_STATUS] Calling API: {endpoint}")
    print(f"[CHECK_CATALOG_STATUS] Attempt: {attempt_count}")

    try:
        # Make the API call
        response = requests.get(
            endpoint,
            headers=headers,
            timeout=30
        )

        print(f"[CHECK_CATALOG_STATUS] Response status: {response.status_code}")
        print(f"[CHECK_CATALOG_STATUS] Response body: {response.text}")

        # Parse response
        if response.status_code == 200:
            catalog_data = response.json()

            # Extract kb_name and data_source_name
            kb_name = catalog_data.get('kb_name')
            data_source_name = catalog_data.get('data_source_name')

            print(f"[CHECK_CATALOG_STATUS] kb_name: {kb_name}")
            print(f"[CHECK_CATALOG_STATUS] data_source_name: {data_source_name}")

            # Check if both are valid (not None, not empty, not "PENDING" or similar)
            kb_valid = kb_name and kb_name.strip() and kb_name.upper() not in ['PENDING', 'NULL', 'NONE', '']
            ds_valid = data_source_name and data_source_name.strip() and data_source_name.upper() not in ['PENDING', 'NULL', 'NONE', '']

            catalog_ready = kb_valid and ds_valid

            print(f"[CHECK_CATALOG_STATUS] KB valid: {kb_valid}, DS valid: {ds_valid}")
            print(f"[CHECK_CATALOG_STATUS] Catalog ready: {catalog_ready}")

            return {
                'success': True,
                'catalog_ready': catalog_ready,
                'kb_name': kb_name,
                'data_source_name': data_source_name,
                'catalog_data': catalog_data,
                'local_catalog_id': local_catalog_id,
                'catalog_name': catalog_name,
                'attempt_count': attempt_count + 1,
                'status_code': response.status_code
            }
        else:
            # API call failed
            error_message = f"API returned status {response.status_code}: {response.text}"
            print(f"[ERROR] {error_message}")

            return {
                'success': False,
                'catalog_ready': False,
                'error': error_message,
                'local_catalog_id': local_catalog_id,
                'catalog_name': catalog_name,
                'attempt_count': attempt_count + 1,
                'status_code': response.status_code
            }

    except requests.exceptions.Timeout:
        error_message = "Request timed out"
        print(f"[ERROR] {error_message}")
        return {
            'success': False,
            'catalog_ready': False,
            'error': error_message,
            'local_catalog_id': local_catalog_id,
            'catalog_name': catalog_name,
            'attempt_count': attempt_count + 1
        }

    except Exception as e:
        error_message = f"Exception occurred: {str(e)}"
        print(f"[ERROR] {error_message}")
        import traceback
        traceback.print_exc()

        return {
            'success': False,
            'catalog_ready': False,
            'error': error_message,
            'local_catalog_id': local_catalog_id,
            'catalog_name': catalog_name,
            'attempt_count': attempt_count + 1
        }
