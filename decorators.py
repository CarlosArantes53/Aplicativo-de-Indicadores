from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Você precisa estar logado para ver esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash('Você precisa estar logado para ver esta página.', 'warning')
                return redirect(url_for('login'))
            
            user_role = session.get('user', {}).get('role')
            if user_role not in allowed_roles:
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Manteremos o admin_required para facilitar, embora roles_required já o cubra
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Acesso negado. Faça login primeiro.', 'danger')
            return redirect(url_for('login'))
        
        user_role = session.get('user', {}).get('role')
        
        if user_role != 'admin':
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('home'))
            
        return f(*args, **kwargs)
    return decorated_function