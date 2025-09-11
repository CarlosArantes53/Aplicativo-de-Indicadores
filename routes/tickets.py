from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from decorators import login_required
from services import ticket_service
import os
from collections.abc import Iterable

tickets_bp = Blueprint('tickets', __name__, url_prefix='/tickets')

def _to_safe_list(x):
    if x is None:
        return []
    if isinstance(x, (str, bytes)):
        return x
    try:
        if hasattr(x, "tolist") and callable(x.tolist):
            return x.tolist()
        if isinstance(x, Iterable):
            return list(x)
    except Exception:
        return x
    return x

@tickets_bp.route('/')
@login_required
def list_tickets():
    user_roles = session['user'].get('roles', {})
    if 'admin' in user_roles:
        tickets = ticket_service.get_all_tickets()
    else:
        user_email = session['user']['email']
        tickets = ticket_service.get_user_tickets(user_email)
        
    return render_template('tickets/list.html', tickets=tickets, is_admin='admin' in user_roles)

@tickets_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_ticket():
    if request.method == 'POST':
        title = request.form.get('title')
        urgency = request.form.get('urgency')
        sector = request.form.get('sector')
        description = request.form.get('description')
        attachment = request.files.get('attachment')
        user_email = session['user']['email']

        if not all([title, urgency, sector, description]):
            flash('Todos os campos são obrigatórios.', 'danger')
            return redirect(url_for('tickets.create_ticket'))

        try:
            ticket_service.create_ticket(title, urgency, sector, description, user_email, attachment)
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

    if not ticket or (ticket['user_email'] != session['user']['email'] and not is_admin):
        flash('Chamado não encontrado ou você não tem permissão para visualizá-lo.', 'danger')
        return redirect(url_for('tickets.list_tickets'))

    if request.method == 'POST':
        if 'reply' in request.form:
            reply_text = request.form.get('reply')
            user_email = session['user']['email']
            if reply_text:
                ticket_service.add_reply_to_ticket(ticket_id, reply_text, user_email)
                flash('Resposta adicionada com sucesso!', 'success')
        
        if 'status' in request.form and is_admin:
            new_status = request.form.get('status')
            ticket_service.update_ticket_status(ticket_id, new_status)
            flash('Status do chamado atualizado com sucesso!', 'success')

        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    if 'responses' in ticket:
        ticket['responses'] = sorted(_to_safe_list(ticket['responses']), key=lambda r: r['timestamp'])

    return render_template('tickets/view.html', ticket=ticket, is_admin=is_admin)