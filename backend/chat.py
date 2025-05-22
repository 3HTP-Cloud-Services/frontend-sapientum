from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

from models import Conversation, Message

db = SQLAlchemy()

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

def generate_ai_response(user_query, catalog_id=None, conversation_id=None, user_id=None):

    #first, let's create a convo if one does not exist.
    if conversation_id == -1:
        # create the convo
        conversation_id = create_new_conversation(user_id, catalog_id)

    #now, create the message that came in
    message_in = Message(
        conversation_id = conversation_id,
        is_request = True,
        prompt = '',
        message = user_query,
        created_at = datetime.now()
    )
    db.session.add(message_in)
    db.session.commit()

    responses = {
        'hola': '¡Hola! ¿Cómo puedo ayudarte hoy?',
        'ayuda': 'Puedo ayudarte con resúmenes de documentos, responder preguntas sobre el sistema o proporcionar orientación sobre la evaluación de competencia de IA.',
        'documento': '¿Qué documento te gustaría que resuma o proporcione información?',
        'resumir': 'Puedo resumir documentos para ti. Por favor, especifica qué documento te gustaría que resuma.',
        'permisos': 'Los permisos de usuario son administrados por los administradores. Hay diferentes niveles de acceso para documentos y funcionalidad de chat.',
        'hello': '¡Hola! ¿Cómo puedo ayudarte hoy?',
        'help': 'Puedo ayudarte con resúmenes de documentos, responder preguntas sobre el sistema o proporcionar orientación sobre la evaluación de competencia de IA.',
    }

    doc_responses = {}
    for doc in DOCUMENTS:
        doc_id = str(doc['id'])
        doc_title = doc['title'].lower()
        doc_responses[f'document {doc_id}'] = f"{doc['title']} - {doc['content'][:150]}..."
        doc_responses[doc_title] = f"{doc['title']} - {doc['content'][:150]}..."

    all_responses = {**responses, **doc_responses}

    lower_query = user_query.lower()

    message_out = Message(
        conversation_id = conversation_id,
        is_request = False,
        prompt = 'system prompt',
        created_at=datetime.now()
    )

    for keyword, response in all_responses.items():
        if keyword in lower_query:
            message_out.response = response
            db.session.add(message_out)
            db.session.commit()
            return response

    for doc in DOCUMENTS:
        title_words = doc['title'].lower().split()
        for word in title_words:
            if len(word) > 3 and word in lower_query:
                msg = f"Encontré un documento que podría interesarte: {doc['title']} - {doc['content'][:100]}..."
                message_out.response = msg
                db.session.add(message_out)
                db.session.commit()
                return msg

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
    return conversation