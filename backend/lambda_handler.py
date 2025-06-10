import os
import sys
import json
import traceback

# Asegurar que el directorio raíz del proyecto esté en el path de Python
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Importar la aplicación Flask
from app import app
from models import db
import backend.db as db_utils

# Usar un adaptador WSGI alternativo
try:
    from awsgi import response
except ImportError:
    print("Error: awsgi no está instalado. Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aws-wsgi"])
    from awsgi import response

def normalize_event(event):
    """Convert Function URL (API Gateway v2) events to API Gateway v1 format for awsgi."""

    # If it's already API Gateway v1 format, return as-is
    if 'httpMethod' in event:
        return event

    # Handle Function URL / API Gateway v2 format
    if 'requestContext' in event and 'http' in event['requestContext']:
        http_context = event['requestContext']['http']

        # Convert to API Gateway v1 format
        normalized_event = {
            'httpMethod': http_context['method'],
            'path': event.get('rawPath', '/'),
            'pathParameters': event.get('pathParameters'),
            'queryStringParameters': event.get('queryStringParameters'),
            'headers': event.get('headers', {}),
            'multiValueHeaders': {},
            'body': event.get('body'),
            'isBase64Encoded': event.get('isBase64Encoded', False),
            'requestContext': {
                'requestId': event['requestContext'].get('requestId', 'lambda-invoke'),
                'stage': 'prod',
                'resourcePath': event.get('rawPath', '/'),
                'httpMethod': http_context['method'],
                'path': event.get('rawPath', '/'),
                'protocol': http_context.get('protocol', 'HTTP/1.1'),
                'identity': event['requestContext'].get('identity', {}),
                'accountId': event['requestContext'].get('accountId', ''),
                'resourceId': 'lambda'
            }
        }
        return normalized_event

    # Fallback for direct invoke or unknown format
    return {
        'httpMethod': 'GET',
        'path': '/',
        'pathParameters': None,
        'queryStringParameters': None,
        'headers': {},
        'multiValueHeaders': {},
        'body': None,
        'isBase64Encoded': False,
        'requestContext': {
            'requestId': 'lambda-invoke',
            'stage': 'prod',
            'resourcePath': '/',
            'httpMethod': 'GET',
            'path': '/',
            'protocol': 'HTTP/1.1',
            'identity': {},
            'accountId': '',
            'resourceId': 'lambda'
        }
    }

def lambda_handler(event, context):
    """AWS Lambda Function entrypoint."""
    try:
        print(f"Event recibido: {json.dumps(event)}")

        # Normalize the event format for awsgi
        normalized_event = normalize_event(event)
        print(f"Event normalizado: {json.dumps(normalized_event)}")

        # Verificar la conexión a la base de datos
        with app.app_context():
            try:
                # Obtener la configuración de la base de datos
                db_config = app.config.get('SQLALCHEMY_DATABASE_URI')
                print(f"Usando configuración de base de datos: {db_config}")

                # Verificar si estamos usando SQLite (fallback)
                if db_config and 'sqlite' in db_config:
                    print("ADVERTENCIA: Usando SQLite como fallback. Verifica los permisos para acceder a PostgreSQL.")

                    # Inicializar la base de datos SQLite
                    try:
                        db.create_all()
                        print("Base de datos SQLite inicializada correctamente")

                        # Crear un usuario de prueba si no existe
                        from models import User
                        if not User.query.filter_by(email="jpnunez@3htp.com").first():
                            test_user = User(
                                email="jpnunez@3htp.com",
                                role="admin",
                                is_admin=True,
                                is_catalog_editor=True,
                                chat_access=True,
                                is_active=True
                            )
                            db.session.add(test_user)
                            db.session.commit()
                            print("Usuario de prueba creado: jpnunez@3htp.com")
                    except Exception as db_init_error:
                        print(f"Error al inicializar la base de datos SQLite: {db_init_error}")
                        print(traceback.format_exc())

                # Probar la conexión
                if db_utils.test_connection(app):
                    print("Conexión a la base de datos exitosa")
                else:
                    print("Error en la conexión a la base de datos")
            except Exception as db_error:
                print(f"Error al verificar la base de datos: {db_error}")
                print(traceback.format_exc())

        # Usar awsgi para manejar la solicitud con el evento normalizado
        return response(app, normalized_event, context)
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        print(f"Error: {error_msg}")
        print(f"Stack trace: {stack_trace}")

        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": error_msg})
        }
