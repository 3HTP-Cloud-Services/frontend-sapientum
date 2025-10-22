"""
Lambda function to update catalog in database with kb_name and data_source_name
This function is called by the Step Function once the catalog is ready
"""
import json
import os
import psycopg2
from psycopg2 import sql


def get_db_connection():
    """Get database connection from environment variables"""
    return psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT', 5432),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD')
    )


def lambda_handler(event, context):
    """
    Update the catalog in the database with kb_name and data_source_name

    Input event should contain:
    - local_catalog_id: The ID of the catalog in the local database
    - kb_name: The knowledge base name to store
    - data_source_name: The data source name to store
    - catalog_data: Full catalog data from API (optional, for logging)

    Returns:
    - success: Whether the update succeeded
    - updated: Whether rows were updated
    - catalog_id: The catalog ID that was updated
    """

    print(f"[UPDATE_CATALOG_DB] Starting - Event: {json.dumps(event)}")

    # Extract inputs from event
    local_catalog_id = event.get('local_catalog_id')
    kb_name = event.get('kb_name')
    data_source_name = event.get('data_source_name')
    catalog_name = event.get('catalog_name')

    if not local_catalog_id:
        print("[ERROR] Missing local_catalog_id in event")
        return {
            'success': False,
            'error': 'Missing local_catalog_id',
            'updated': False
        }

    if not kb_name or not data_source_name:
        print("[ERROR] Missing kb_name or data_source_name in event")
        return {
            'success': False,
            'error': 'Missing kb_name or data_source_name',
            'updated': False,
            'catalog_id': local_catalog_id
        }

    print(f"[UPDATE_CATALOG_DB] Updating catalog ID: {local_catalog_id}")
    print(f"[UPDATE_CATALOG_DB] kb_name: {kb_name}")
    print(f"[UPDATE_CATALOG_DB] data_source_name: {data_source_name}")

    try:
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update the catalog record
        update_query = sql.SQL("""
            UPDATE catalog
            SET knowledge_base_id = %s,
                data_source_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """)

        cursor.execute(update_query, (kb_name, data_source_name, local_catalog_id))
        rows_updated = cursor.rowcount

        conn.commit()

        print(f"[UPDATE_CATALOG_DB] Updated {rows_updated} row(s)")

        # Verify the update
        cursor.execute("SELECT id, name, knowledge_base_id, data_source_id FROM catalog WHERE id = %s", (local_catalog_id,))
        updated_record = cursor.fetchone()

        cursor.close()
        conn.close()

        if updated_record:
            print(f"[UPDATE_CATALOG_DB] Verified update: {updated_record}")

        result = {
            'success': True,
            'updated': rows_updated > 0,
            'rows_updated': rows_updated,
            'catalog_id': local_catalog_id,
            'catalog_name': catalog_name,
            'kb_name': kb_name,
            'data_source_name': data_source_name
        }

        print(f"[UPDATE_CATALOG_DB] Success: {json.dumps(result)}")
        return result

    except Exception as e:
        error_message = f"Database error: {str(e)}"
        print(f"[ERROR] {error_message}")
        import traceback
        traceback.print_exc()

        return {
            'success': False,
            'error': error_message,
            'updated': False,
            'catalog_id': local_catalog_id
        }
