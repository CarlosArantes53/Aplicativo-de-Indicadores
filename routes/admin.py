from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.user import get_all_users, create_user_with_role, get_user_data, update_user_role
from decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/users')
@admin_required
def manage_users():
    id_token = session['user']['idToken']
    users = get_all_users(token=id_token)
    return render_template('admin/manage_users.html', users=users)

@admin_bp.route('/user/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not all([email, password, role]):
            flash('Todos os campos são obrigatórios.', 'danger')
            return redirect(url_for('admin.create_user'))

        try:
            admin_token = session['user']['idToken']
            create_user_with_role(email, password, role, admin_token=admin_token)
            flash(f'Usuário {email} criado com sucesso!', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            flash(f'Erro ao criar usuário: {e}', 'danger')

    return render_template('admin/user_form.html', action='create', user={})

@admin_bp.route('/user/edit/<uid>', methods=['GET', 'POST'])
@admin_required
def edit_user(uid):
    id_token = session['user']['idToken']
    user_data = get_user_data(uid, token=id_token)
    if not user_data:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('admin.manage_users'))

    if request.method == 'POST':
        role = request.form.get('role')
        if update_user_role(uid, role, token=id_token):
            flash(f'Nível do usuário {user_data["email"]} atualizado com sucesso!', 'success')
        else:
            flash('Erro ao atualizar o nível do usuário.', 'danger')
        return redirect(url_for('admin.manage_users'))

    return render_template('admin/user_form.html', action='edit', user=user_data, user_uid=uid)