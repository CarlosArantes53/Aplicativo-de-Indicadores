import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import os

def format_value(value, is_currency=True):
    if pd.isna(value) or value is None:
        return "R$ 0" if is_currency else "0"
    if is_currency:
        return f"R$ {int(value):,}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        return f"{int(value):,}".replace(",", ".")

def calculate_commercial_kpis(start_date_str, end_date_str):
    kpis_data = {}
    chart_data = None
    error = None
    parquet_path = os.getenv('PARQUET_ANALISE_VENDA_HEAD')

    if not parquet_path:
        error = "Caminho do arquivo Parquet não definido na variável de ambiente 'PARQUET_ANALISE_VENDA_HEAD'."
        return kpis_data, chart_data, error

    if not os.path.exists(parquet_path):
        error = f"Arquivo de dados '{parquet_path}' não encontrado. Verifique o caminho."
        return kpis_data, chart_data, error

    try:
        df = pd.read_parquet(parquet_path)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        mask = (df['Data'] >= start_date) & (df['Data'] <= end_date)
        filtered_df = df.loc[mask]

        if filtered_df.empty:
            return {}, None, None
        
        # --- Cálculo dos KPIs (sem alteração) ---
        summary = filtered_df.groupby('TipoNs').agg(
            Valor=('ValorTotal', 'sum'),
            Peso=('PesoTotal', 'sum'),
            Quantidade=('DocNum', 'count')
        ).reset_index()
        
        nf_saida_val = summary.loc[summary['TipoNs'] == 'NOTA FISCAL DE SAÍDA', 'Valor'].sum()
        cancel_val = summary.loc[summary['TipoNs'] == 'CANCELAMENTO', 'Valor'].sum()
        devolucao_val = summary.loc[summary['TipoNs'] == 'DEVOLUÇÃO', 'Valor'].sum()

        nf_saida_peso = summary.loc[summary['TipoNs'] == 'NOTA FISCAL DE SAÍDA', 'Peso'].sum()
        cancel_peso = summary.loc[summary['TipoNs'] == 'CANCELAMENTO', 'Peso'].sum()
        devolucao_peso = summary.loc[summary['TipoNs'] == 'DEVOLUÇÃO', 'Peso'].sum()

        nf_saida_qtd = summary.loc[summary['TipoNs'] == 'NOTA FISCAL DE SAÍDA', 'Quantidade'].sum()
        cancel_qtd = summary.loc[summary['TipoNs'] == 'CANCELAMENTO', 'Quantidade'].sum()
        devolucao_qtd = summary.loc[summary['TipoNs'] == 'DEVOLUÇÃO', 'Quantidade'].sum()

        net_revenue_valor = nf_saida_val + cancel_val + devolucao_val
        net_revenue_peso = nf_saida_peso + cancel_peso + devolucao_peso
        net_revenue_qtd = nf_saida_qtd + cancel_qtd + devolucao_qtd

        kpis_list = summary.to_dict('records')
        for kpi in kpis_list:
            kpi['Valor_fmt'] = format_value(kpi['Valor'])
            kpi['Peso_fmt'] = format_value(kpi['Peso'], is_currency=False) + " kg"
            kpi['Quantidade_fmt'] = format_value(kpi['Quantidade'], is_currency=False)
        
        kpis_list.append({
            'TipoNs': 'FATURAMENTO LÍQUIDO',
            'Valor_fmt': format_value(net_revenue_valor),
            'Peso_fmt': format_value(net_revenue_peso, is_currency=False) + " kg",
            'Quantidade_fmt': format_value(net_revenue_qtd, is_currency=False)
        })
        
        kpis_data = {item['TipoNs']: item for item in kpis_list}

        # --- NOVO: Preparação dos dados para o gráfico ---
        df_saida = filtered_df[filtered_df['TipoNs'] == 'NOTA FISCAL DE SAÍDA'].copy()
        if not df_saida.empty:
            df_saida.loc[:, 'Data'] = df_saida['Data'].dt.date
            daily_agg = df_saida.groupby('Data').agg(
                Faturamento=('ValorTotal', 'sum'),
                Peso=('PesoTotal', 'sum')
            ).reset_index()
            daily_agg = daily_agg.sort_values(by='Data')
            
            chart_data = {
                'labels': [d.strftime('%d/%m') for d in daily_agg['Data']],
                'faturamento_data': daily_agg['Faturamento'].tolist(),
                'peso_data': daily_agg['Peso'].tolist()
            }

    except Exception as e:
        error = f"Erro ao processar o arquivo de dados: {e}"

    return kpis_data, chart_data, error