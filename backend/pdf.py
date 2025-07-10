from datetime import datetime
from flask import jsonify
from models import db, Conversation, Message, Catalog
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from io import BytesIO
import textwrap

def generate_conversation_pdf(catalog_id, user_id, message_count=20):
    """
    Generate a PDF of the conversation for a specific user and catalog.
    
    Args:
        catalog_id: ID of the catalog
        user_id: ID of the user
        message_count: Number of messages to include (default 20)
    
    Returns:
        tuple: (pdf_data, filename) if successful, (None, error_message) if failed
    """
    try:
        # Validate message count
        if not isinstance(message_count, int) or message_count <= 0:
            return None, "Invalid message count"

        # Find the conversation for this user and catalog
        conversation = Conversation.query.filter_by(
            speaker_id=user_id,
            catalog_id=catalog_id
        ).first()

        if not conversation:
            return None, "No conversation found"

        # Get catalog info
        catalog = db.session.get(Catalog, catalog_id)
        if not catalog:
            return None, "Catalog not found"

        # Get the last N messages for this conversation, ordered by creation time
        messages = Message.query.filter_by(
            conversation_id=conversation.id
        ).order_by(Message.created_at.desc()).limit(message_count).all()
        
        # Reverse to get chronological order
        messages = list(reversed(messages))

        if not messages:
            return None, "No messages found in conversation"

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        # Container for the 'Flowable' objects
        story = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        user_style = ParagraphStyle(
            'UserMessage',
            parent=styles['Normal'],
            fontSize=10,
            leftIndent=20,
            rightIndent=20,
            spaceAfter=12,
            backColor='#E3F2FD'
        )
        
        system_style = ParagraphStyle(
            'SystemMessage',
            parent=styles['Normal'],
            fontSize=10,
            leftIndent=20,
            rightIndent=20,
            spaceAfter=12,
            backColor='#F5F5F5'
        )
        
        header_style = ParagraphStyle(
            'MessageHeader',
            parent=styles['Normal'],
            fontSize=8,
            textColor='#666666',
            spaceAfter=6,
            leftIndent=20
        )

        # Add title
        title_text = f"Conversation: {catalog.name}"
        story.append(Paragraph(title_text, title_style))
        
        # Add metadata
        metadata_text = f"Downloaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>Messages: {len(messages)}"
        story.append(Paragraph(metadata_text, styles['Normal']))
        story.append(Spacer(1, 20))

        # Add messages
        for msg in messages:
            # Message header with timestamp
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if msg.created_at else 'Unknown time'
            message_type = "You" if msg.is_request else "AI Assistant"
            header_text = f"{message_type} - {timestamp}"
            story.append(Paragraph(header_text, header_style))
            
            # Message content
            content = msg.message.replace('\n', '<br/>')
            # Escape HTML characters
            content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            content = content.replace('&lt;br/&gt;', '<br/>')
            
            message_style = user_style if msg.is_request else system_style
            story.append(Paragraph(content, message_style))
            story.append(Spacer(1, 10))

        # Build PDF
        doc.build(story)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()

        # Create filename
        from app import sanitize_filename_for_header
        safe_catalog_name = sanitize_filename_for_header(catalog.name)
        filename = f"conversation_{safe_catalog_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return pdf_data, filename

    except Exception as e:
        return None, f"Error generating PDF: {str(e)}"