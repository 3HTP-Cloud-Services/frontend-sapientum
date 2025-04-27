from botocore.exceptions import ClientError
from aws_utils import get_dynamodb_table


def get_all_catalogs():
    try:
        table = get_dynamodb_table('sapientum_catalogs')
        response = table.scan()
        catalogs = response.get('Items', [])
        
        return catalogs
    except ClientError as e:
        print(f"Error getting catalogs: {e}")
        return []


def get_catalog_by_id(catalog_id):
    try:
        table = get_dynamodb_table('sapientum_catalogs')
        response = table.get_item(
            Key={
                'catalog_name': catalog_id
            }
        )
        return response.get('Item')
    except ClientError as e:
        print(f"Error getting catalog {catalog_id}: {e}")
        return None