from flask import Blueprint, render_template
from decorators import login_required, roles_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/home')
@login_required
def home():
    return render_template('home.html')

@main_bp.route('/setor/comercial')
@roles_required(allowed_roles=['admin', 'comercial', 'diretoria'])
def setor_comercial():
    return render_template('setores/comercial.html')

@main_bp.route('/setor/financeiro')
@roles_required(allowed_roles=['admin', 'financeiro', 'diretoria'])
def setor_financeiro():
    return render_template('setores/financeiro.html')