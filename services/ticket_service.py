import os
from datetime import datetime
from werkzeug.utils import secure_filename
from models.ticket import db, Ticket, Response, Attachment

UPLOAD_FOLDER = 'uploads/tickets'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'mp4', 'mov', 'avi'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _save_attachments(files, ticket_id, response_id=None):
    """Salva os arquivos de anexo e retorna os objetos Attachment."""
    attachment_objects = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            if response_id:
                filename = f"{ticket_id}_response_{response_id}_{timestamp}_{original_filename}"
            else:
                filename = f"{ticket_id}_ticket_{timestamp}_{original_filename}"
                
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            new_attachment = Attachment(
                filepath=filepath,
                filename=original_filename,
                ticket_id=ticket_id,
                response_id=response_id
            )
            attachment_objects.append(new_attachment)
    return attachment_objects


def get_all_tickets():
    """Carrega todos os chamados do banco de dados."""
    return Ticket.query.order_by(Ticket.created_at.desc()).all()

def get_user_tickets(user_email):
    """Carrega os chamados de um usuário específico."""
    return Ticket.query.filter_by(user_email=user_email).order_by(Ticket.created_at.desc()).all()

def get_ticket_by_id(ticket_id):
    """Busca um ticket pelo seu ID."""
    return Ticket.query.get(ticket_id)

def add_reply_to_ticket(ticket_id, reply_text, user_email, attachments=None):
    """Adiciona uma resposta a um chamado."""
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        return False

    new_reply = Response(
        ticket_id=ticket_id,
        text=reply_text,
        user_email=user_email,
        timestamp=datetime.utcnow()
    )
    
    db.session.add(new_reply)
    db.session.commit() # Commit para obter o ID da nova resposta

    if attachments:
        attachment_objects = _save_attachments(attachments, ticket_id, response_id=new_reply.id)
        for att in attachment_objects:
            db.session.add(att)
        db.session.commit()
        
    return True

def create_ticket(title, urgency, sector, description, user_email, attachments=None):
    """Cria um novo chamado e o salva no banco de dados."""
    new_ticket = Ticket(
        title=title,
        urgency=urgency,
        sector=sector,
        description=description,
        user_email=user_email,
        status='Aberto',
        created_at=datetime.utcnow()
    )
    db.session.add(new_ticket)
    db.session.commit() # Commit para obter o ID do novo ticket

    if attachments:
        attachment_objects = _save_attachments(attachments, ticket_id=new_ticket.id)
        for att in attachment_objects:
            db.session.add(att)
        db.session.commit()
    
    return new_ticket.id

def update_ticket_status(ticket_id, new_status):
    """Atualiza o status de um chamado."""
    ticket = get_ticket_by_id(ticket_id)
    if ticket:
        ticket.status = new_status
        db.session.commit()
        return True
    return False