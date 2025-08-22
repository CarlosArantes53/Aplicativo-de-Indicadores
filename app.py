import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from config import auth
from models.user import get_user_data, get_all_users, create_user_with_role, update_user_role
from decorators import login_required, admin_required, roles_required

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('home'))

    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user_auth_data = auth.sign_in_with_email_and_password(email, password)
            uid = user_auth_data['localId']
            id_token = user_auth_data['idToken']
            
            user_db_data = get_user_data(uid, id_token)
            
            session['user'] = {
                'uid': uid,
                'email': user_auth_data['email'],
                'idToken': id_token,
                'role': user_db_data.get('role', 'default') if user_db_data else 'default'
            }
            return redirect(url_for('home'))
        except Exception as e:
            error = 'Falha na autenticação. Verifique suas credenciais.'
            
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    session.pop('user', None)
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login'))

# --- ROTAS PRINCIPAIS ---
@app.route('/home')
@login_required
def home():
    return render_template('home.html')

# --- ROTAS DOS SETORES (INDICADORES) ---
@app.route('/setor/comercial')
@roles_required(allowed_roles=['admin', 'comercial', 'diretoria'])
def setor_comercial():
    # No futuro, você importará e chamará as funções de 'indicators/setor_comercial.py'
    # Ex: data = indicators.setor_comercial.get_data()
    return render_template('setores/comercial.html')

@app.route('/setor/financeiro')
@roles_required(allowed_roles=['admin', 'financeiro', 'diretoria'])
def setor_financeiro():
    # Ex: data = indicators.setor_financeiro.get_data()
    return render_template('setores/financeiro.html')


# --- ROTAS DE ADMINISTRAÇÃO ---
@app.route('/admin/users')
@admin_required
def manage_users():
    id_token = session['user']['idToken']
    users = get_all_users(token=id_token)
    return render_template('admin/manage_users.html', users=users)

@app.route('/admin/user/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not all([email, password, role]):
            flash('Todos os campos são obrigatórios.', 'danger')
            return redirect(url_for('create_user'))

        try:
            admin_token = session['user']['idToken']
            create_user_with_role(email, password, role, admin_token=admin_token)
            flash(f'Usuário {email} criado com sucesso!', 'success')
            return redirect(url_for('manage_users'))
        except Exception as e:
            flash(f'Erro ao criar usuário: {e}', 'danger')

    return render_template('admin/user_form.html', action='create', user={})

@app.route('/admin/user/edit/<uid>', methods=['GET', 'POST'])
@admin_required
def edit_user(uid):
    id_token = session['user']['idToken']
    user_data = get_user_data(uid, token=id_token)
    if not user_data:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('manage_users'))

    if request.method == 'POST':
        role = request.form.get('role')
        if update_user_role(uid, role, token=id_token):
            flash(f'Nível do usuário {user_data["email"]} atualizado com sucesso!', 'success')
        else:
            flash('Erro ao atualizar o nível do usuário.', 'danger')
        return redirect(url_for('manage_users'))

    return render_template('admin/user_form.html', action='edit', user=user_data, user_uid=uid)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)