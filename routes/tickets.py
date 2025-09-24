from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_from_directory
from decorators import login_required
from models.ticket import Attachment
from models.user import get_all_users
from services import ticket_service
from datetime import datetime
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
        # ... (código existente sem alterações)
        try:
            ticket_service.create_ticket(
                request.form.get('title'),
                request.form.get('urgency'),
                request.form.get('sector'),
                request.form.get('description'),
                session['user']['email'],
                request.files.getlist('attachments'),
                request.form.get('deadline'),
                request.form.get('tags')
            )
            flash('Chamado criado com sucesso!', 'success')
            return redirect(url_for('tickets.list_tickets'))
        except Exception as e:
            flash(f'Erro ao criar chamado: {e}', 'danger')

    return render_template('tickets/create.html', now=datetime.now())


@tickets_bp.route('/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def view_ticket(ticket_id):
    user_roles = session['user'].get('roles', {})
    is_admin = 'admin' in user_roles
    user_email = session['user']['email']
    
    ticket = ticket_service.get_ticket_by_id(ticket_id)

    if not ticket or (ticket.user_email != user_email and not is_admin):
        flash('Chamado não encontrado ou você não tem permissão para visualizá-lo.', 'danger')
        return redirect(url_for('tickets.list_tickets'))

    all_users = []
    if is_admin:
        id_token = session['user']['idToken']
        all_users_dict = get_all_users(token=id_token)
        all_users = [{'email': data['email']} for uid, data in all_users_dict.items() if 'email' in data]

    if request.method == 'POST':
        form_action = request.form.get('form_action')

        if form_action == 'add_interaction':
            ticket_service.process_new_interaction(
                ticket_id, user_email, request.form, request.files.getlist('attachments')
            )
            flash('Interação adicionada com sucesso!', 'success')
        
        elif form_action == 'admin_update' and is_admin:
            ticket_service.update_ticket_admin(
                ticket_id, user_email, 
                request.form.get('status'), 
                request.form.get('assignee')
            )
            flash('Chamado atualizado com sucesso!', 'success')
            
        elif form_action == 'provide_validation':
            ticket_service.process_validation_response(ticket_id, user_email, request.form)
            flash('Validação registrada com sucesso!', 'success')
            
        elif form_action == 'update_interaction_status' and is_admin:
            interaction_id = request.form.get('interaction_id')
            new_status = request.form.get('new_status')
            ticket_service.update_interaction_status(interaction_id, new_status, user_email)
            flash('Status da ação atualizado!', 'success')

        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    return render_template('tickets/view.html', ticket=ticket, is_admin=is_admin, all_users=all_users, now=datetime.now())



@tickets_bp.route('/download/attachment/<int:attachment_id>')
@login_required
def download_file(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    
    user_roles = session['user'].get('roles', {})
    is_admin = 'admin' in user_roles
    user_email = session['user']['email']
    
    ticket = attachment.ticket or (attachment.interaction.ticket if attachment.interaction else None)
    
    if not ticket or (ticket.user_email != user_email and not is_admin):
        flash('Você não tem permissão para acessar este arquivo.', 'danger')
        return redirect(url_for('tickets.list_tickets'))

    directory = os.path.dirname(attachment.filepath)
    filename = os.path.basename(attachment.filepath)
    
    return send_from_directory(directory, filename, as_attachment=False)