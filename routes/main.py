from flask import Blueprint, render_template, redirect, url_for, request, flash
from decorators import login_required, roles_required
from services.commercial_service import calculate_commercial_kpis
from datetime import date
from dateutil.relativedelta import relativedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/home')
@login_required
def home():
    return render_template('home.html')

@main_bp.route('/setor/comercial')
@roles_required(allowed_roles=['admin', 'comercial', 'diretoria'])
def setor_comercial():
    return redirect(url_for('main.comercial_geral'))

@main_bp.route('/setor/comercial/geral')
@roles_required(allowed_roles=['admin', 'comercial', 'diretoria'])
def comercial_geral():
    
    today = date.today()
    first_day_prev_month = (today.replace(day=1) - relativedelta(months=1))
    last_day_prev_month = (today.replace(day=1) - relativedelta(days=1))

    start_date_str = request.args.get('start_date', default=first_day_prev_month.strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', default=last_day_prev_month.strftime('%Y-%m-%d'))

    kpis, chart_data, error = calculate_commercial_kpis(start_date_str, end_date_str)

    if error:
        flash(error, "danger")

    return render_template('setores/comercial/geral.html', 
                           kpis=kpis, 
                           chart_data=chart_data,
                           start_date=start_date_str, 
                           end_date=end_date_str)


@main_bp.route('/setor/comercial/conversao')
@roles_required(allowed_roles=['admin', 'comercial', 'diretoria'])
def comercial_conversao():
    return render_template('setores/comercial/conversao.html')

@main_bp.route('/setor/comercial/cancelamentos')
@roles_required(allowed_roles=['admin', 'comercial', 'diretoria'])
def comercial_cancelamentos():
    return render_template('setores/comercial/cancelamentos.html')

@main_bp.route('/setor/comercial/metas')
@roles_required(allowed_roles=['admin', 'comercial', 'diretoria'])
def comercial_metas():
    return render_template('setores/comercial/metas.html')

@main_bp.route('/setor/financeiro')
@roles_required(allowed_roles=['admin', 'financeiro', 'diretoria'])
def setor_financeiro():
    return render_template('setores/financeiro.html')