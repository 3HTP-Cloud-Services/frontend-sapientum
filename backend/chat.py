from datetime import datetime
import json
import re

from aws_utils import invoke_lambda_with_sigv4_v2, call_backend_lambda
from models import db, Conversation, Message, Catalog, File, Version
from aws_utils import invoke_lambda_with_sigv4, get_lambda_url, get_agent_id, get_agent_alias_id

DOCUMENTS = [
    {
        "id": 1,
        "title": "Procedimientos de Evaluación de Competencia de IA",
        "content": "Este documento describe métricas para medir el rendimiento de la IA incluyendo precisión, tiempo de respuesta y amplitud de conocimiento. El documento también analiza estrategias de implementación para diversos contextos organizacionales y mejores prácticas para evaluar la competencia de IA en diferentes dominios. La evaluación debe incluir tanto métricas cuantitativas como evaluaciones cualitativas."
    },
    {
        "id": 2,
        "title": "Estrategias de Implementación para Sistemas de IA",
        "content": "Este documento describe estrategias de implementación para sistemas de IA en varios contextos organizacionales, incluyendo mejores prácticas para despliegue e integración. Cubre consideraciones técnicas, gestión de partes interesadas y técnicas de mitigación de riesgos. El documento también proporciona un marco para evaluar la preparación organizacional para la adopción de IA."
    },
    {
        "id": 3,
        "title": "Casos de Estudio de Implementación de IA",
        "content": "Este documento proporciona casos de estudio de implementaciones exitosas de IA con análisis detallado de resultados y lecciones aprendidas. Cada caso de estudio examina los desafíos enfrentados, soluciones implementadas y resultados logrados. El documento concluye con patrones comunes y mejores prácticas derivadas de estos ejemplos del mundo real."
    }
]

def parse_file_references(text):
    """
    Parse file references in format 33-44-55.<extension> and replace with download links
    Returns the text with file references replaced by HTML links
    """
    file_pattern = r'\b(\d+)-(\d+)-(\d+)\.([a-zA-Z]{2,6})\b'

    def replace_file_reference(match):
        catalog_id = int(match.group(1))
        file_id = int(match.group(2))
        version_id = int(match.group(3))
        extension = match.group(4)

        file_info = get_file_info(catalog_id, file_id, version_id)
        if file_info:
            download_url = f"/api/download/{version_id}"
            filename = file_info['filename']
            return f'<a href="{download_url}" download="{filename}">{filename}</a>'
        else:
            return match.group(0)

    return re.sub(file_pattern, replace_file_reference, text)

def get_file_info(catalog_id, file_id, version_id):
    """
    Get file information for catalog_id-file_id-version_id combination
    Returns dict with filename and other metadata if found, None otherwise
    """
    try:
        version = Version.query.join(File).join(Catalog).filter(
            Version.id == version_id,
            File.id == file_id,
            Catalog.id == catalog_id
        ).first()

        if version:
            return {
                'filename': version.filename,
                'file_name': version.file.name,
                'catalog_name': version.file.catalog.name,
                'size': version.size,
                'created_at': version.created_at.isoformat() if version.created_at else None
            }
        return None
    except Exception as e:
        print(f"Error looking up file info for {catalog_id}-{file_id}-{version_id}: {e}")
        return None

def get_conversation(user_id, catalog_id):
    existing_conversation = Conversation.query.filter_by(
        speaker_id=user_id,
        catalog_id=catalog_id
    ).first()

    if existing_conversation:
        return existing_conversation.id

    conversation = create_new_conversation(user_id, catalog_id)
    return conversation.id

def generate_ai_response(user_query, catalog_id=None, user_id=None, jwt=None, client_ip=None):
    print('\ngenerate_ai_response:', user_query, catalog_id, user_id, jwt, 'client_ip:', client_ip)
    conversation_id = get_conversation(user_id, catalog_id)

    # Prepare origin info with client IP
    origin_info = f"ip:{client_ip or 'unknown'}"

    # Save the user's message to the database
    message_in = Message(
        conversation_id = conversation_id,
        is_request = True,
        prompt = '',
        message = user_query,
        created_at = datetime.now(),
        origin = origin_info
    )
    db.session.add(message_in)
    db.session.commit()

    # Create a placeholder for the AI response with same origin info initially
    message_out = Message(
        conversation_id = conversation_id,
        is_request = False,
        prompt = 'system prompt',
        created_at = datetime.now(),
        origin = origin_info
    )
    db.session.add(message_out)
    db.session.commit()

    try:
        # Prepare the request payload for the Lambda function
        payload = {
            'message': user_query,
            'conversation_id': conversation_id,
            'catalog_id': catalog_id,
            'user_id': user_id,
            'agent_id': get_agent_id(),
            'agent_alias_id': get_agent_alias_id(),
            'enable_trace': True,
            'jwt_token': jwt
        }
        print('\ngenerate_ai_response: payload:', payload)

        # Get the Lambda function URL from config
        lambda_url = get_lambda_url()

        # Call the Lambda function using SigV4 authentication
        print(f"Calling Lambda function at {lambda_url} with payload: {payload}")
        lambda_response = call_backend_lambda(payload)

        print(f"Lambda response: {lambda_response}")
        print(f"Lambda response type: {type(lambda_response)}")
        if lambda_response and isinstance(lambda_response, dict):
            print(f"Lambda response keys: {list(lambda_response.keys())}")
        lambda_instance_id = "unknown"
        trace_data = None

        # Process the Lambda response
        if lambda_response and isinstance(lambda_response, dict):
            # Extract Lambda instance ID if available
            if 'lambda_instance_id' in lambda_response:
                lambda_instance_id = lambda_response['lambda_instance_id']
            elif 'requestId' in lambda_response:
                lambda_instance_id = lambda_response['requestId']

            # Extract trace events if present and tracing is enabled
            if 'trace_events' in lambda_response and payload.get('enable_trace', False):
                import json
                trace_data = json.dumps(lambda_response['trace_events'])
            # Extract assistant_response.text from the Lambda response
            if 'assistant_response' in lambda_response and 'text' in lambda_response['assistant_response']:
                print("getting a response from lambda: ", lambda_response['assistant_response']['text'])
                ai_response = lambda_response['assistant_response']['text']

                # Extract agent_session_id from the Lambda response and update the conversation
                if 'agent_session_id' in lambda_response:
                    agent_session_id = lambda_response['agent_session_id']
                    print(f"Updating conversation with agent_session_id: {agent_session_id}")
                    conversation = Conversation.query.get(conversation_id)
                    if conversation:
                        conversation.session_id = agent_session_id
                        db.session.commit()
            elif 'response' in lambda_response:
                # Fallback to old response format if assistant_response.text is not available
                print("falling back to old response format: ", lambda_response['response'])
                ai_response = lambda_response['response']
            else:
                # Fallback to document search if Lambda response doesn't have expected fields
                print("lambda response doesn't have expected fields, falling back to document search")
                ai_response = search_documents(user_query)
        else:
            # Fallback to document search if Lambda call fails
            print("no response from lambda, falling back to document search")
            ai_response = search_documents(user_query)

        print("final response: ", ai_response)

        # Parse file references and replace with download links
        processed_response = parse_file_references(ai_response)

        # Update the AI message with response content, Lambda instance info, and trace data
        updated_origin = f"ip:{client_ip or 'unknown'},lambda:{lambda_instance_id}"
        message_out.message = processed_response
        message_out.origin = updated_origin
        if trace_data:
            message_out.trace = trace_data
        db.session.commit()

        return processed_response, message_in.id

    except Exception as e:
        print(f"Error generating AI response: {e}")
        import traceback
        traceback.print_exc()

        # Fallback to document search if an error occurs
        fallback_response = search_documents(user_query)

        # Parse file references and replace with download links
        processed_fallback = parse_file_references(fallback_response)

        # Update the message in the database with fallback origin info
        fallback_origin = f"ip:{client_ip or 'unknown'},lambda:fallback"
        message_out.message = processed_fallback
        message_out.origin = fallback_origin
        db.session.commit()

        return processed_fallback


def search_documents(query):
    """Search for relevant documents based on the query"""
    lower_query = query.lower()

    for doc in DOCUMENTS:
        title_words = doc['title'].lower().split()
        for word in title_words:
            if len(word) > 3 and word in lower_query:
                return f"Encontré un documento que podría interesarte: {doc['title']} - {doc['content'][:100]}..."

    return "No estoy seguro de entender tu pregunta. ¿Podrías reformularla o proporcionar más detalles?"

def create_new_conversation(user_id, catalog_id):
    curr_date = datetime.now().strftime("%Y-%m-%d") # by default, let's use the date as the convo
    conversation = Conversation(
        catalog_id=catalog_id,
        speaker_id=user_id,
        title=curr_date,
        session_id=''
    )
    db.session.add(conversation)
    db.session.commit()
    print(f"Created new conversation with ID {conversation.id} {conversation.title}")
    return conversation
