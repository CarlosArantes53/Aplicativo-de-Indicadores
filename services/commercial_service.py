import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import os

def format_value(value, is_currency=True):
    if pd.isna(value) or value is None:
        return "R$ 0,00" if is_currency else "0"
    if is_currency:
        return f"R$ {int(value):,}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        return f"{int(value):,}".replace(",", ".")

def calculate_commercial_kpis(start_date_str, end_date_str):
    kpis_data = {}
    chart_data = None
    error = None
    path_head = os.getenv('PARQUET_ANALISE_VENDA_HEAD')
    path_line = os.getenv('PARQUET_ANALISE_VENDA_LINE')

    if not path_head or not path_line:
        error = "Variáveis de ambiente 'PARQUET_ANALISE_VENDA_HEAD' e/ou 'PARQUET_ANALISE_VENDA_LINE' não definidas."
        return kpis_data, chart_data, error
    if not os.path.exists(path_head):
        error = f"Arquivo de dados '{path_head}' não encontrado."
        return kpis_data, chart_data, error
    if not os.path.exists(path_line):
        error = f"Arquivo de dados '{path_line}' não encontrado."
        return kpis_data, chart_data, error

    try:
        df_head = pd.read_parquet(path_head)
        df_line = pd.read_parquet(path_line)
        
        df_head['Data'] = pd.to_datetime(df_head['Data'], errors='coerce')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        mask = (df_head['Data'] >= start_date) & (df_head['Data'] <= end_date)
        filtered_df_head = df_head.loc[mask].copy()

        if filtered_df_head.empty:
            return {}, None, "Nenhum dado encontrado para o período selecionado."
        
        summary = filtered_df_head.groupby('TipoNs').agg(
            Valor=('ValorTotal', 'sum'),
            Peso=('PesoTotal', 'sum'),
            Quantidade=('DocNum', 'count')
        ).reset_index()
        
        nf_saida_val = summary.loc[summary['TipoNs'] == 'NOTA FISCAL DE SAÍDA', 'Valor'].sum()
        cancel_val = summary.loc[summary['TipoNs'] == 'CANCELAMENTO', 'Valor'].sum()
        devolucao_val = summary.loc[summary['TipoNs'] == 'DEVOLUÇÃO', 'Valor'].sum()
        net_revenue_valor = nf_saida_val + cancel_val + devolucao_val

        nf_saida_peso = summary.loc[summary['TipoNs'] == 'NOTA FISCAL DE SAÍDA', 'Peso'].sum()
        cancel_peso = summary.loc[summary['TipoNs'] == 'CANCELAMENTO', 'Peso'].sum()
        devolucao_peso = summary.loc[summary['TipoNs'] == 'DEVOLUÇÃO', 'Peso'].sum()
        nf_saida_qtd = summary.loc[summary['TipoNs'] == 'NOTA FISCAL DE SAÍDA', 'Quantidade'].sum()
        cancel_qtd = summary.loc[summary['TipoNs'] == 'CANCELAMENTO', 'Quantidade'].sum()
        devolucao_qtd = summary.loc[summary['TipoNs'] == 'DEVOLUÇÃO', 'Quantidade'].sum()
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

        line_totals = df_line.groupby('LctoContabil').agg(
            TotalBruto=('TotalBruto', 'sum'),
            TotalLinha=('TotalLinha', 'sum')
        ).reset_index()

        df_merged = pd.merge(
            filtered_df_head,
            line_totals,
            on='LctoContabil',
            how='left'
        )

        df_saida = df_merged[df_merged['TipoNs'] != 'ANULAÇÃO'].copy()

        if not df_saida.empty:
            df_saida.loc[:, 'Data'] = df_saida['Data'].dt.date
            
            daily_agg = df_saida.groupby('Data').agg(
                Faturamento=('ValorTotal', 'sum'),
                Peso=('PesoTotal', 'sum'),
                TotalBruto=('TotalBruto', 'sum'),
                TotalLinha=('TotalLinha', 'sum')
            ).reset_index()

            daily_agg = daily_agg.sort_values(by='Data')
            
            daily_agg['Preco_por_kg'] = daily_agg.apply(
                lambda row: row['Faturamento'] / row['Peso'] if row['Peso'] > 0 else 0, axis=1
            )
            
            daily_agg['Desconto_medio'] = daily_agg.apply(
                lambda row: ((row['TotalBruto'] - row['TotalLinha']) / row['TotalBruto']) * 100 if row['TotalBruto'] > 0 else 0, axis=1
            )
            
            chart_data = {
                'labels': [d.strftime('%d/%m') for d in daily_agg['Data']],
                'faturamento_data': daily_agg['Faturamento'].tolist(),
                'peso_data': daily_agg['Peso'].tolist(),
                'preco_kg_data': daily_agg['Preco_por_kg'].tolist(),
                'desconto_data': daily_agg['Desconto_medio'].tolist()
            }

    except Exception as e:
        error = f"Erro ao processar o arquivo de dados: \"{e}\""

    return kpis_data, chart_data, error