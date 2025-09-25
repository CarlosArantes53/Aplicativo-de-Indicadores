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

    # Opções para os dropdowns / checkboxes de filtro (definidas antes dos args)
    filter_options = {
        'statuses': ['Aberto', 'Em Andamento', 'Aguardando Resposta', 'Fechado'],
        'urgencies': ['Baixa', 'Média', 'Alta', 'Crítica'],
        'sectors': ['TI', 'Financeiro', 'Comercial', 'RH', 'Operacional']
    }

    # --- STATUS (comportamento que você já tinha) ---
    statuses = request.args.getlist('status')
    # se não veio nenhum parâmetro status (ou seja, 'status' não está na query), aplicar default parcial
    if not statuses and 'status' not in request.args:
        statuses = ['Aberto', 'Em Andamento', 'Aguardando Resposta']

    # --- URGENCY e SECTOR: por padrão marcar todos os filtros ---
    urgencies = request.args.getlist('urgency')
    if not urgencies and 'urgency' not in request.args:
        # marca todas as urgências por padrão
        urgencies = list(filter_options['urgencies'])

    sectors = request.args.getlist('sector')
    if not sectors and 'sector' not in request.args:
        # marca todos os setores por padrão
        sectors = list(filter_options['sectors'])

    filters = {
        'status': statuses,
        'urgency': urgencies,
        'sector': sectors,
        'title': request.args.get('title', '')
    }
    # Remove chaves vazias para não filtrar por ''
    filters = {k: v for k, v in filters.items() if v}

    sorting = {
        'by': request.args.get('sort_by', 'created_at'),
        'order': request.args.get('order', 'desc')
    }

    if is_admin:
        tickets = ticket_service.get_all_tickets(filters=filters, sorting=sorting)
    else:
        user_email = session['user']['email']
        tickets = ticket_service.get_user_tickets(user_email, filters=filters, sorting=sorting)

    return render_template('tickets/list.html',
                           tickets=tickets,
                           is_admin=is_admin,
                           filter_options=filter_options,
                           current_filters=filters,
                           current_sorting=sorting)



@tickets_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_ticket():
    if request.method == 'POST':
        try:
            stages = []
            if request.form.get('ticket_type') == 'projeto':
                stage_names = request.form.getlist('stage_name[]')
                stage_deadlines = request.form.getlist('stage_deadline[]')
                for name, deadline in zip(stage_names, stage_deadlines):
                    if name: # Adiciona apenas se o nome da etapa não estiver vazio
                        stages.append({'name': name, 'deadline': deadline})

            ticket_service.create_ticket(
                title=request.form.get('title'),
                urgency=request.form.get('urgency'),
                sector=request.form.get('sector'),
                description=request.form.get('description'),
                user_email=session['user']['email'],
                attachments=request.files.getlist('attachments'),
                deadline=request.form.get('deadline'),
                ticket_type=request.form.get('ticket_type'),
                stages=stages
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
            
        elif form_action == 'update_stage_status' and is_admin:
            stage_id = request.form.get('stage_id')
            new_status = request.form.get('new_status')
            ticket_service.update_project_stage_status(stage_id, new_status)
            flash('Status da etapa atualizado!', 'success')


        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    
    stage_filter = request.args.get('stage_filter')
    interactions = ticket.interactions
    if stage_filter and stage_filter.isdigit():
        interactions = [i for i in ticket.interactions if i.project_stage_id == int(stage_filter)]
    elif stage_filter == 'geral':
        interactions = [i for i in ticket.interactions if i.project_stage_id is None]


    return render_template('tickets/view.html', 
                           ticket=ticket, 
                           is_admin=is_admin, 
                           all_users=all_users, 
                           now=datetime.now(),
                           interactions=interactions,
                           stage_filter=stage_filter)



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