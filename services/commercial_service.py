import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import os

def format_value(value, is_currency=True):
    """Função auxiliar para formatar números para exibição no frontend."""
    if pd.isna(value) or value is None:
        return "R$ 0,00" if is_currency else "0"
    if is_currency:
        # Formata para o padrão brasileiro (ex: R$ 1.234,56)
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        # Garante que o número seja inteiro antes de formatar
        return f"{int(value):,}".replace(",", ".")

def calculate_commercial_kpis(start_date_str, end_date_str):
    """
    Lê o arquivo Parquet, filtra por data e calcula os KPIs comerciais.
    Retorna um dicionário com os KPIs formatados e um possível erro.
    """
    kpis_data = {}
    error = None
    parquet_path = "C:/Users/carlos.eduardo/Desktop/Automação Power BI/data/analise_venda_head.parquet"

    if not os.path.exists(parquet_path):
        error = f"Arquivo de dados '{parquet_path}' não encontrado. Verifique o caminho."
        return kpis_data, error

    try:
        df = pd.read_parquet(parquet_path)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        mask = (df['Data'] >= start_date) & (df['Data'] <= end_date)
        filtered_df = df.loc[mask]

        if filtered_df.empty:
            return {}, None # Retorna dicionário vazio se não houver dados no período

        summary = filtered_df.groupby('TipoNs').agg(
            Valor=('ValorTotal', 'sum'),
            Peso=('PesoTotal', 'sum'),
            Quantidade=('DocNum', 'count')
        ).reset_index()
        
        # --- Cálculo do Faturamento Líquido ---
        nf_saida_val = summary.loc[summary['TipoNs'] == 'NOTA FISCAL DE SAÍDA', 'Valor'].sum()
        cancel_val = summary.loc[summary['TipoNs'] == 'CANCELAMENTO', 'Valor'].sum()
        devolucao_val = summary.loc[summary['TipoNs'] == 'DEVOLUÇÃO', 'Valor'].sum()
        
        nf_saida_peso = summary.loc[summary['TipoNs'] == 'NOTA FISCAL DE SAÍDA', 'Peso'].sum()
        cancel_peso = summary.loc[summary['TipoNs'] == 'CANCELAMENTO', 'Peso'].sum()
        devolucao_peso = summary.loc[summary['TipoNs'] == 'DEVOLUÇÃO', 'Peso'].sum()

        net_revenue_valor = nf_saida_val - cancel_val - devolucao_val
        net_revenue_peso = nf_saida_peso - cancel_peso - devolucao_peso

        # Formatação para exibição
        kpis_list = summary.to_dict('records')
        for kpi in kpis_list:
            kpi['Valor_fmt'] = format_value(kpi['Valor'])
            kpi['Peso_fmt'] = format_value(kpi['Peso'], is_currency=False) + " kg"
            kpi['Quantidade_fmt'] = format_value(kpi['Quantidade'], is_currency=False)
        
        # Adiciona o KPI de Faturamento Líquido calculado
        kpis_list.append({
            'TipoNs': 'FATURAMENTO LÍQUIDO',
            'Valor_fmt': format_value(net_revenue_valor),
            'Peso_fmt': format_value(net_revenue_peso, is_currency=False) + " kg"
        })
        
        # Converte a lista de dicionários em um dicionário aninhado para fácil acesso no template
        kpis_data = {item['TipoNs']: item for item in kpis_list}

    except Exception as e:
        error = f"Erro ao processar o arquivo de dados: {e}"

    return kpis_data, error