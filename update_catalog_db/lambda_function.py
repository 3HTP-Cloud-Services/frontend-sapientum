"""
Lambda function to update catalog in database via backend API
This function is called by the Step Function once the catalog is ready
"""
import json
import os
import requests


def lambda_handler(event, context):
    """
    Update the catalog in the database via backend API

    Input event should contain:
    - local_catalog_id: The ID of the catalog in the local database
    - kb_name: The knowledge base ID to store
    - data_source_name: The data source ID to store
    - agent_id: The agent ID
    - agent_alias_id: The agent alias ID
    - jwt_token: JWT token for authentication

    Returns:
    - success: Whether the update succeeded
    - catalog_id: The catalog ID that was updated
    """

    print(f"[UPDATE_CATALOG_DB] ===== STARTING =====")
    print(f"[UPDATE_CATALOG_DB] Full event received:")
    print(json.dumps(event, indent=2))

    # Extract inputs from event
    local_catalog_id = event.get('local_catalog_id')
    kb_name = event.get('kb_name')
    data_source_name = event.get('data_source_name')
    agent_id = event.get('agent_id')
    agent_alias_id = event.get('agent_alias_id')
    catalog_name = event.get('catalog_name')
    jwt_token = event.get('jwt_token')

    if not local_catalog_id:
        print("[UPDATE_CATALOG_DB] ERROR: Missing local_catalog_id in event")
        return {
            'success': False,
            'error': 'Missing local_catalog_id',
            'updated': False
        }

    if not kb_name or not data_source_name:
        print("[UPDATE_CATALOG_DB] ERROR: Missing kb_name or data_source_name in event")
        return {
            'success': False,
            'error': 'Missing kb_name or data_source_name',
            'updated': False,
            'catalog_id': local_catalog_id
        }

    if not jwt_token:
        print("[UPDATE_CATALOG_DB] ERROR: Missing jwt_token in event")
        return {
            'success': False,
            'error': 'Missing jwt_token for authentication',
            'updated': False,
            'catalog_id': local_catalog_id
        }

    print(f"[UPDATE_CATALOG_DB] Will update catalog ID: {local_catalog_id}")
    print(f"[UPDATE_CATALOG_DB] knowledge_base_id: {kb_name}")
    print(f"[UPDATE_CATALOG_DB] data_source_id: {data_source_name}")
    print(f"[UPDATE_CATALOG_DB] agent_id: {agent_id}")
    print(f"[UPDATE_CATALOG_DB] agent_alias_id: {agent_alias_id}")

    try:
        # Call the backend API endpoint
        backend_url = "https://kf75zv6hbtup4a7cpjx2daat2q0lwgnt.lambda-url.us-east-1.on.aws"
        endpoint = f"{backend_url}/api/catalogs/{local_catalog_id}/update-aws-resources"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {jwt_token}"
        }

        payload = {
            "knowledge_base_id": kb_name,
            "data_source_id": data_source_name,
            "agent_id": agent_id,
            "agent_alias_id": agent_alias_id
        }

        print(f"[UPDATE_CATALOG_DB] Calling backend API: {endpoint}")
        print(f"[UPDATE_CATALOG_DB] Payload:")
        print(json.dumps(payload, indent=2))

        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )

        print(f"[UPDATE_CATALOG_DB] Response status: {response.status_code}")
        print(f"[UPDATE_CATALOG_DB] Response body:")
        print(response.text)

        if response.status_code == 200:
            backend_result = response.json()
            print(f"[UPDATE_CATALOG_DB] ===== SUCCESS =====")
            print(json.dumps(backend_result, indent=2))

            # Return comprehensive result including backend response
            return {
                'success': True,
                'catalog_id': local_catalog_id,
                'backend_response': backend_result,
                'backend_status': response.status_code,
                'message': 'Database updated successfully via backend API'
            }
        else:
            error_msg = f"Backend API returned status {response.status_code}: {response.text}"
            print(f"[UPDATE_CATALOG_DB] ERROR: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'updated': False,
                'catalog_id': local_catalog_id,
                'backend_status': response.status_code,
                'backend_response': response.text
            }

    except Exception as e:
        error_message = f"Error calling backend API: {str(e)}"
        print(f"[UPDATE_CATALOG_DB] ERROR: {error_message}")
        import traceback
        traceback.print_exc()

        return {
            'success': False,
            'error': error_message,
            'updated': False,
            'catalog_id': local_catalog_id
        }
