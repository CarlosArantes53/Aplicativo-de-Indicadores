import os
from datetime import datetime
from werkzeug.utils import secure_filename
from models.ticket import db, Ticket, Interaction, Attachment
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import desc, asc
import random

UPLOAD_FOLDER = 'uploads/tickets'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'mp4', 'mov', 'avi'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _save_attachments(files, ticket_id, interaction_id=None):
    """Salva os arquivos de anexo e retorna os objetos Attachment."""
    attachment_objects = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            if interaction_id:
                filename = f"{ticket_id}_interaction_{interaction_id}_{timestamp}_{original_filename}"
            else:
                filename = f"{ticket_id}_ticket_{timestamp}_{original_filename}"
                
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            new_attachment = Attachment(
                filepath=filepath,
                filename=original_filename,
                ticket_id=ticket_id,
                interaction_id=interaction_id
            )
            attachment_objects.append(new_attachment)
    return attachment_objects


def get_all_tickets(filters=None, sorting=None):
    """Carrega todos os chamados do banco de dados com filtros e ordenação."""
    query = Ticket.query

    if filters:
        if filters.get('status'):
            query = query.filter(Ticket.status == filters['status'])
        if filters.get('urgency'):
            query = query.filter(Ticket.urgency == filters['urgency'])
        if filters.get('sector'):
            query = query.filter(Ticket.sector == filters['sector'])
        if filters.get('title'):
            query = query.filter(Ticket.title.ilike(f"%{filters['title']}%"))

    if sorting and sorting.get('by') in ['id', 'urgency', 'status', 'created_at', 'title', 'sector']:
        direction = desc if sorting.get('order') == 'desc' else asc
        query = query.order_by(direction(getattr(Ticket, sorting['by'])))
    else:
        # Default sort
        query = query.order_by(Ticket.created_at.desc())

    return query.all()

def get_user_tickets(user_email, filters=None, sorting=None):
    """Carrega os chamados de um usuário específico com filtros e ordenação."""
    query = Ticket.query.filter_by(user_email=user_email)

    if filters:
        if filters.get('status'):
            query = query.filter(Ticket.status == filters['status'])
        if filters.get('urgency'):
            query = query.filter(Ticket.urgency == filters['urgency'])
        if filters.get('sector'):
            query = query.filter(Ticket.sector == filters['sector'])
        if filters.get('title'):
            query = query.filter(Ticket.title.ilike(f"%{filters['title']}%"))

    if sorting and sorting.get('by') in ['id', 'urgency', 'status', 'created_at', 'title', 'sector']:
        direction = desc if sorting.get('order') == 'desc' else asc
        query = query.order_by(direction(getattr(Ticket, sorting['by'])))
    else:
        # Default sort
        query = query.order_by(Ticket.created_at.desc())

    return query.all()

def get_ticket_by_id(ticket_id):
    """Busca um ticket pelo seu ID."""
    return Ticket.query.get(ticket_id)

def add_interaction(ticket_id, user_email, action_type, text=None, interaction_data=None, deadline=None, parent_id=None):
    """Cria uma nova interação para um chamado."""
    deadline_obj = None
    if deadline:
        try:
            deadline_obj = datetime.fromisoformat(deadline)
        except (ValueError, TypeError):
            deadline_obj = None

    interaction = Interaction(
        ticket_id=ticket_id,
        user_email=user_email,
        action_type=action_type,
        text=text,
        interaction_data=interaction_data,
        deadline=deadline_obj,
        parent_id=parent_id
    )
    db.session.add(interaction)
    db.session.commit()
    return interaction

def process_new_interaction(ticket_id, user_email, form_data, files):
    """Processa o formulário para adicionar uma nova interação (comentário, ação, etc.)."""
    action = form_data.get('action')
    text = form_data.get('reply_text')
    deadline = form_data.get('interaction_deadline')
    external_system = form_data.get('external_system')
    external_ticket_id = form_data.get('external_ticket_id')
    
    interaction_data = {}
    if external_system or external_ticket_id:
        interaction_data['external_system'] = external_system
        interaction_data['external_ticket_id'] = external_ticket_id

    if action == 'request_validation':
        interaction_data['validation_status'] = 'pending'
        new_interaction = add_interaction(
            ticket_id, user_email, action_type='request_validation',
            text=text, deadline=deadline,
            interaction_data=interaction_data
        )
    else: # Ação padrão é 'comment'
        new_interaction = add_interaction(
            ticket_id, user_email, action_type='comment', text=text,
            interaction_data=interaction_data if interaction_data else None
        )

    if files:
        attachment_objects = _save_attachments(files, ticket_id, interaction_id=new_interaction.id)
        for att in attachment_objects:
            db.session.add(att)
        db.session.commit()


def process_validation_response(ticket_id, user_email, form_data):
    """Processa a resposta do usuário a um pedido de validação."""
    parent_interaction_id = form_data.get('parent_interaction_id')
    validation_status = form_data.get('validation_response') # 'approved' or 'rejected'
    
    parent_interaction = Interaction.query.get(parent_interaction_id)
    if not parent_interaction or parent_interaction.ticket_id != ticket_id:
        return # Segurança: não pertence a este ticket
    
    # Atualiza a interação PAI (o pedido) com o resultado
    parent_interaction.interaction_data['validation_status'] = validation_status
    flag_modified(parent_interaction, "interaction_data")
    
    # Cria a interação FILHA (a resposta)
    add_interaction(
        ticket_id=ticket_id,
        user_email=user_email,
        action_type='provide_validation',
        parent_id=parent_interaction_id,
        interaction_data={'validation_status': validation_status}
    )
    db.session.commit()

def create_ticket(title, urgency, sector, description, user_email, attachments=None, deadline=None):
    """Cria um novo chamado e o salva no banco de dados."""
    deadline_obj = None
    if deadline:
        try:
            deadline_obj = datetime.fromisoformat(deadline)
        except ValueError:
            deadline_obj = None

    new_ticket = Ticket(
        title=title,
        urgency=urgency,
        sector=sector,
        description=description,
        user_email=user_email,
        status='Aberto',
        created_at=datetime.utcnow(),
        deadline=deadline_obj
    )

    db.session.add(new_ticket)