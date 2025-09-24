from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_from_directory
from decorators import login_required
from models.ticket import Attachment
from services import ticket_service
import os

tickets_bp = Blueprint('tickets', __name__, url_prefix='/tickets')

@tickets_bp.route('/')
@login_required
def list_tickets():
    user_roles = session['user'].get('roles', {})
    is_admin = 'admin' in user_roles
    
    if is_admin:
        tickets = ticket_service.get_all_tickets()
    else:
        user_email = session['user']['email']
        tickets = ticket_service.get_user_tickets(user_email)
        
    return render_template('tickets/list.html', tickets=tickets, is_admin=is_admin)


@tickets_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_ticket():
    if request.method == 'POST':
        title = request.form.get('title')
        urgency = request.form.get('urgency')
        sector = request.form.get('sector')
        description = request.form.get('description')
        attachments = request.files.getlist('attachments')
        user_email = session['user']['email']

        if not all([title, urgency, sector, description]):
            flash('Todos os campos são obrigatórios.', 'danger')
            return redirect(url_for('tickets.create_ticket'))

        try:
            ticket_service.create_ticket(title, urgency, sector, description, user_email, attachments)
            flash('Chamado criado com sucesso!', 'success')
            return redirect(url_for('tickets.list_tickets'))
        except Exception as e:
            flash(f'Erro ao criar chamado: {e}', 'danger')

    return render_template('tickets/create.html')


@tickets_bp.route('/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def view_ticket(ticket_id):
    user_roles = session['user'].get('roles', {})
    is_admin = 'admin' in user_roles
    
    ticket = ticket_service.get_ticket_by_id(ticket_id)

    if not ticket or (ticket.user_email != session['user']['email'] and not is_admin):
        flash('Chamado não encontrado ou você não tem permissão para visualizá-lo.', 'danger')
        return redirect(url_for('tickets.list_tickets'))

    if request.method == 'POST':
        # Tratamento para resposta
        if 'reply' in request.form and request.form.get('reply'):
            reply_text = request.form.get('reply')
            user_email = session['user']['email']
            attachments = request.files.getlist('attachments')
            ticket_service.add_reply_to_ticket(ticket_id, reply_text, user_email, attachments)
            flash('Resposta adicionada com sucesso!', 'success')
        
        # Tratamento para mudança de status
        if 'status' in request.form and is_admin:
            new_status = request.form.get('status')
            ticket_service.update_ticket_status(ticket_id, new_status)
            flash('Status do chamado atualizado com sucesso!', 'success')

        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    return render_template('tickets/view.html', ticket=ticket, is_admin=is_admin)



@tickets_bp.route('/download/attachment/<int:attachment_id>')
@login_required
def download_file(attachment_id):
    # Busca o anexo pelo ID no banco de dados
    attachment = Attachment.query.get_or_404(attachment_id)
    
    # Lógica de permissão (opcional mas recomendado):
    # Verifica se o usuário tem permissão para ver este anexo
    user_roles = session['user'].get('roles', {})
    is_admin = 'admin' in user_roles
    user_email = session['user']['email']
    
    ticket = attachment.ticket or (attachment.response.ticket if attachment.response else None)
    
    if not ticket or (ticket.user_email != user_email and not is_admin):
        flash('Você não tem permissão para acessar este arquivo.', 'danger')
        return redirect(url_for('tickets.list_tickets'))

    # Extrai o diretório e o nome do arquivo do caminho salvo
    directory = os.path.dirname(attachment.filepath)
    filename = os.path.basename(attachment.filepath)
    
    # Usa send_from_directory para servir o arquivo de forma segura
    return send_from_directory(directory, filename, as_attachment=False) # as_attachment=False tenta exibir no navegador
