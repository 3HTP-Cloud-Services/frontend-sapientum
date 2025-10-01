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
    print(f'[DEBUG] get_conversation called with user_id: {user_id}, catalog_id: {catalog_id}')
    try:
        existing_conversation = Conversation.query.filter_by(
            speaker_id=user_id,
            catalog_id=catalog_id
        ).first()
        print(f'[DEBUG] Query for existing conversation completed')

        if existing_conversation:
            print(f'[DEBUG] Found existing conversation with id: {existing_conversation.id}')
            return existing_conversation.id

        print(f'[DEBUG] No existing conversation found, creating new one')
        conversation = create_new_conversation(user_id, catalog_id)
        print(f'[DEBUG] Created new conversation with id: {conversation.id}')
        return conversation.id
    except Exception as e:
        print(f'[ERROR] Error in get_conversation: {e}')
        raise e

def generate_ai_response(user_query, catalog_id=None, user_id=None, jwt=None, client_ip=None):
    print('\ngenerate_ai_response:', user_query, catalog_id, user_id, jwt, 'client_ip:', client_ip)
    print(f'[DEBUG] Starting generate_ai_response - user_id: {user_id}, catalog_id: {catalog_id}')
    
    try:
        conversation_id = get_conversation(user_id, catalog_id)
        print(f'[DEBUG] Got conversation_id: {conversation_id}')
    except Exception as e:
        print(f'[ERROR] Failed to get conversation: {e}')
        raise e

    # Prepare origin info with client IP
    origin_info = f"ip:{client_ip or 'unknown'}"

    # Save the user's message to the database
    try:
        print(f'[DEBUG] Creating user message - conversation_id: {conversation_id}, origin: {origin_info}')
        message_in = Message(
            conversation_id = conversation_id,
            is_request = True,
            prompt = '',
            message = user_query,
            created_at = datetime.now(),
            origin = origin_info
        )
        db.session.add(message_in)
        print(f'[DEBUG] Added user message to session, attempting commit')
        db.session.commit()
        print(f'[DEBUG] Successfully committed user message with id: {message_in.id}')
    except Exception as e:
        print(f'[ERROR] Failed to save user message: {e}')
        db.session.rollback()
        raise e

    # Create a placeholder for the AI response with same origin info initially
    try:
        print(f'[DEBUG] Creating AI response placeholder - conversation_id: {conversation_id}')
        message_out = Message(
            conversation_id = conversation_id,
            is_request = False,
            prompt = 'system prompt',
            created_at = datetime.now(),
            origin = origin_info
        )
        db.session.add(message_out)
        print(f'[DEBUG] Added AI response placeholder to session, attempting commit')
        db.session.commit()
        print(f'[DEBUG] Successfully committed AI response placeholder with id: {message_out.id}')
    except Exception as e:
        print(f'[ERROR] Failed to create AI response placeholder: {e}')
        db.session.rollback()
        raise e

    try:
        print(f"[STEP 1] Retrieving conversation from database...")
        print(f"[STEP 1] conversation_id: {conversation_id}")

        conversation = Conversation.query.get(conversation_id)

        if conversation:
            print(f"[STEP 1] ✓ Conversation found - ID: {conversation.id}, Title: {conversation.title}")
            print(f"[STEP 1] Conversation session_id: {conversation.session_id}")
            existing_session_id = conversation.session_id if conversation.session_id else None
        else:
            print(f"[STEP 1] ✗ WARNING: Conversation not found for ID: {conversation_id}")
            existing_session_id = None

        print(f"\n[STEP 2] Building payload for new Lambda URL service...")

        agent_id = get_agent_id()
        agent_alias_id = get_agent_alias_id()

        print(f"[STEP 2] agent_id: {agent_id}")
        print(f"[STEP 2] agent_alias_id: {agent_alias_id}")
        print(f"[STEP 2] message length: {len(user_query)} characters")
        print(f"[STEP 2] enable_trace: True")

        catalog = Catalog.query.get(catalog_id)
        catalog_name = catalog.name if catalog else f"catalog_{catalog_id}"
        print(f"[STEP 2] catalog_name: {catalog_name}")

        payload = {
            'agent_id': agent_id,
            'agent_alias_id': agent_alias_id,
            'message': user_query,
            'jwt_token': jwt,
            'catalog_id': str(catalog_id),
            'catalog_name': catalog_name,
            'enable_trace': True
        }

        if existing_session_id:
            payload['agent_session_id'] = existing_session_id
            print(f"[STEP 2] ✓ Adding agent_session_id to payload: {existing_session_id}")
            print(f"[STEP 2] This is a CONTINUING conversation")
        else:
            print(f"[STEP 2] ✓ No existing session_id - this is a NEW conversation")
            print(f"[STEP 2] Lambda will generate a new agent_session_id")

        print(f"\n[STEP 2] Complete payload:")
        print(f"{payload}")

        print(f"\n[STEP 3] Preparing to call Lambda URL endpoint...")
        lambda_url = get_lambda_url()
        print(f"[STEP 3] Lambda URL: {lambda_url}")
        print(f"[STEP 3] HTTP Method: POST")
        print(f"[STEP 3] Service: lambda")
        print(f"[STEP 3] Headers: Content-Type: application/json")

        print(f"\n[STEP 4] Invoking Lambda URL with SigV4 authentication...")
        import time
        start_time = time.time()

        try:
            lambda_response = invoke_lambda_with_sigv4(
                url=lambda_url,
                method='POST',
                service='lambda',
                body=payload,
                headers={'Content-Type': 'application/json'}
            )
            elapsed_time = time.time() - start_time
            print(f"[STEP 4] ✓ Lambda URL call completed successfully in {elapsed_time:.2f} seconds")

        except Exception as lambda_error:
            elapsed_time = time.time() - start_time
            print(f"[STEP 4] ✗ Lambda URL call FAILED after {elapsed_time:.2f} seconds")
            print(f"[STEP 4] Error type: {type(lambda_error).__name__}")
            print(f"[STEP 4] Error message: {str(lambda_error)}")
            import traceback
            print(f"[STEP 4] Traceback:")
            traceback.print_exc()
            raise lambda_error

        print(f"\n[STEP 5] Processing Lambda response...")
        print(f"[STEP 5] Response type: {type(lambda_response)}")

        if lambda_response is None:
            print(f"[STEP 5] ✗ WARNING: Lambda response is None")
        elif isinstance(lambda_response, dict):
            print(f"[STEP 5] ✓ Response is a dictionary")
            print(f"[STEP 5] Response keys: {list(lambda_response.keys())}")
            print(f"[STEP 5] Response content (first 500 chars): {str(lambda_response)[:500]}")
        else:
            print(f"[STEP 5] Response content: {lambda_response}")
        lambda_instance_id = "unknown"
        trace_data = None

        print(f"\n[STEP 6] Extracting data from Lambda response...")

        if lambda_response and isinstance(lambda_response, dict):
            if 'lambda_instance_id' in lambda_response:
                lambda_instance_id = lambda_response['lambda_instance_id']
                print(f"[STEP 6] ✓ Found lambda_instance_id: {lambda_instance_id}")
            elif 'requestId' in lambda_response:
                lambda_instance_id = lambda_response['requestId']
                print(f"[STEP 6] ✓ Found requestId: {lambda_instance_id}")
            else:
                print(f"[STEP 6] No lambda_instance_id or requestId in response")

            if 'trace_events' in lambda_response and payload.get('enable_trace', False):
                import json
                trace_data = json.dumps(lambda_response['trace_events'])
                print(f"[STEP 6] ✓ Found trace_events, length: {len(trace_data)} characters")
            else:
                print(f"[STEP 6] No trace_events in response")

            if 'assistant_response' in lambda_response and 'text' in lambda_response['assistant_response']:
                ai_response = lambda_response['assistant_response']['text']
                print(f"[STEP 6] ✓ Found assistant_response.text, length: {len(ai_response)} characters")
                print(f"[STEP 6] Response preview: {ai_response[:200]}...")

                if 'agent_session_id' in lambda_response:
                    agent_session_id = lambda_response['agent_session_id']
                    print(f"[STEP 6] ✓ Found agent_session_id: {agent_session_id}")
                    print(f"[STEP 6] Updating conversation {conversation_id} with new session_id...")

                    conversation = Conversation.query.get(conversation_id)
                    if conversation:
                        conversation.session_id = agent_session_id
                        db.session.commit()
                        print(f"[STEP 6] ✓ Conversation session_id updated successfully")
                    else:
                        print(f"[STEP 6] ✗ WARNING: Could not find conversation to update")
                else:
                    print(f"[STEP 6] No agent_session_id in response (may already be set)")

            elif 'response' in lambda_response:
                ai_response = lambda_response['response']
                print(f"[STEP 6] ✓ Found 'response' field (fallback format), length: {len(ai_response)} characters")
                print(f"[STEP 6] Response preview: {ai_response[:200]}...")
            else:
                print(f"[STEP 6] ✗ No 'assistant_response.text' or 'response' field found")
                print(f"[STEP 6] Available fields: {list(lambda_response.keys())}")
                print(f"[STEP 6] Falling back to local document search...")
                ai_response = search_documents(user_query)
        else:
            print(f"[STEP 6] ✗ Invalid or empty response from Lambda")
            print(f"[STEP 6] Falling back to local document search...")
            ai_response = search_documents(user_query)

        print(f"\n[STEP 7] Final AI response prepared")
        print(f"[STEP 7] Response length: {len(ai_response)} characters")
        print(f"[STEP 7] Has trace data: {trace_data is not None}")
        print(f"[STEP 7] Lambda instance ID: {lambda_instance_id}")

        print(f"\n[STEP 8] Parsing file references in response...")
        processed_response = parse_file_references(ai_response)
        if processed_response != ai_response:
            print(f"[STEP 8] ✓ File references were parsed and replaced with download links")
        else:
            print(f"[STEP 8] No file references found in response")

        print(f"\n[STEP 9] Updating AI message in database...")
        try:
            updated_origin = f"ip:{client_ip or 'unknown'},lambda:{lambda_instance_id}"
            print(f"[STEP 9] Setting message origin: {updated_origin}")
            print(f"[STEP 9] Message ID to update: {message_out.id}")

            message_out.message = processed_response
            message_out.origin = updated_origin

            if trace_data:
                message_out.trace = trace_data
                print(f"[STEP 9] ✓ Trace data attached to message")
            else:
                print(f"[STEP 9] No trace data to attach")

            print(f"[STEP 9] Committing to database...")
            db.session.commit()
            print(f"[STEP 9] ✓ AI message successfully saved to database")

        except Exception as e:
            print(f"[STEP 9] ✗ FAILED to update AI message in database")
            print(f"[STEP 9] Error type: {type(e).__name__}")
            print(f"[STEP 9] Error message: {str(e)}")
            db.session.rollback()
            print(f"[STEP 9] Database transaction rolled back")
            raise e

        print(f"\n[STEP 10] ✓ Chat processing completed successfully")
        print(f"[STEP 10] Returning response (length: {len(processed_response)}) and message_id: {message_in.id}")
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
        try:
            fallback_origin = f"ip:{client_ip or 'unknown'},lambda:fallback"
            print(f"[DEBUG] Updating AI message with fallback response, origin: {fallback_origin}")
            message_out.message = processed_fallback
            message_out.origin = fallback_origin
            print(f"[DEBUG] Attempting to commit fallback AI message")
            db.session.commit()
            print(f"[DEBUG] Successfully committed fallback AI message")
        except Exception as e:
            print(f"[ERROR] Failed to update AI message with fallback: {e}")
            db.session.rollback()
            raise e

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
    print(f'[DEBUG] create_new_conversation called with user_id: {user_id}, catalog_id: {catalog_id}')
    try:
        curr_date = datetime.now().strftime("%Y-%m-%d") # by default, let's use the date as the convo
        print(f'[DEBUG] Creating conversation with title: {curr_date}')
        conversation = Conversation(
            catalog_id=catalog_id,
            speaker_id=user_id,
            title=curr_date,
            session_id=''
        )
        db.session.add(conversation)
        print(f'[DEBUG] Added conversation to session, attempting commit')
        db.session.commit()
        print(f"[DEBUG] Successfully created new conversation with ID {conversation.id} {conversation.title}")
        return conversation
    except Exception as e:
        print(f'[ERROR] Failed to create new conversation: {e}')
        db.session.rollback()
        raise e
