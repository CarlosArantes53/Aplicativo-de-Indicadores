from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from decorators import login_required
from services import ticket_service
import os
from collections.abc import Iterable

tickets_bp = Blueprint('tickets', __name__, url_prefix='/tickets')

def _to_safe_list(x):
    """
    Normaliza iteráveis para list para que Jinja possa avaliá-los com segurança.
    - None -> []
    - strings/bytes -> retornam como estão (não convertidas)
    - objetos com tolist() (ex: numpy.ndarray) -> usa tolist()
    - outros iteráveis -> list(x)
    - fallback -> retorna x original
    """
    if x is None:
        return []
    if isinstance(x, (str, bytes)):
        return x
    try:
        # numpy arrays e similares costumam ter tolist()
        if hasattr(x, "tolist") and callable(x.tolist):
            return x.tolist()
        if isinstance(x, Iterable):
            return list(x)
    except Exception:
        # em caso de erro, deixamos o valor original (defensivo)
        return x
    return x

@tickets_bp.route('/')
@login_required
def list_tickets():
    user_email = session['user']['email']
    tickets = ticket_service.get_user_tickets(user_email)
    return render_template('tickets/list.html', tickets=tickets)

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

@tickets_bp.route('/<ticket_id>', methods=['GET', 'POST'])
@login_required
def view_ticket(ticket_id):
    if request.method == 'POST':
        reply_text = request.form.get('reply')
        user_email = session['user']['email']
        if reply_text:
            ticket_service.add_reply_to_ticket(ticket_id, reply_text, user_email)
            flash('Resposta adicionada com sucesso!', 'success')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    ticket = ticket_service.get_ticket_by_id(ticket_id)
    if not ticket or ticket['user_email'] != session['user']['email']:
        flash('Chamado não encontrado ou você não tem permissão para visualizá-lo.', 'danger')
        return redirect(url_for('tickets.list_tickets'))

    # -------------------------
    # Normaliza ticket['responses']
    # -------------------------
    if 'responses' in ticket:
        ticket['responses'] = _to_safe_list(ticket['responses'])
    # -------------------------

    return render_template('tickets/view.html', ticket=ticket)
