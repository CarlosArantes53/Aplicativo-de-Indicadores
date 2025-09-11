import ast
import numpy as np
import pandas as pd
import os
from datetime import datetime

TICKETS_FILE = 'tickets.parquet'
UPLOAD_FOLDER = 'uploads/tickets'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_all_tickets():
    """Carrega todos os chamados do arquivo Parquet."""
    if not os.path.exists(TICKETS_FILE):
        return []
    
    df = pd.read_parquet(TICKETS_FILE)
    return df.to_dict('records')

def get_user_tickets(user_email):
    """Carrega os chamados de um usuário específico do arquivo Parquet."""
    if not os.path.exists(TICKETS_FILE):
        return []
    
    df = pd.read_parquet(TICKETS_FILE)
    user_tickets = df[df['user_email'] == user_email]
    return user_tickets.to_dict('records')

def get_ticket_by_id(ticket_id):
    """Busca um ticket e normaliza a coluna 'responses' para sempre devolver uma lista de dicts."""
    if not os.path.exists(TICKETS_FILE):
        return None

    df = pd.read_parquet(TICKETS_FILE)
    ticket_df = df[df['id'] == ticket_id]

    if ticket_df.empty:
        return None

    ticket = ticket_df.to_dict('records')[0]

    # NÃO usar: responses = ticket.get('responses') or []
    responses = ticket.get('responses', None)

    # Normaliza None -> []
    if responses is None:
        responses = []

    # numpy array / pandas Series -> list
    if isinstance(responses, (np.ndarray, pd.Series)):
        try:
            responses = responses.tolist()
        except Exception:
            responses = list(responses)

    # string que contém representação literal -> eval seguro
    if isinstance(responses, str):
        try:
            parsed = ast.literal_eval(responses)
            if isinstance(parsed, list):
                responses = parsed
            elif isinstance(parsed, dict):
                responses = [parsed]
            else:
                responses = []
        except Exception:
            responses = []

    # dict único -> lista com um elemento
    if isinstance(responses, dict):
        responses = [responses]

    # qualquer outro iterável (exceto str/bytes) -> list
    if not isinstance(responses, list):
        try:
            if hasattr(responses, '__iter__') and not isinstance(responses, (str, bytes)):
                responses = list(responses)
            else:
                responses = []
        except Exception:
            responses = []

    # converte timestamps para datetime (opcional / adaptável ao seu formato)
    normalized = []
    for r in responses:
        if not isinstance(r, dict):
            continue
        ts = r.get('timestamp')
        try:
            if isinstance(ts, pd.Timestamp):
                r['timestamp'] = ts.to_pydatetime()
            elif isinstance(ts, str):
                r['timestamp'] = pd.to_datetime(ts).to_pydatetime()
            # se já for datetime, ok
        except Exception:
            r['timestamp'] = None
        normalized.append(r)

    ticket['responses'] = normalized
    return ticket



def add_reply_to_ticket(ticket_id, reply_text, user_email):
    """Adiciona reply criando uma nova lista (não mutando shareable lists)."""
    if not os.path.exists(TICKETS_FILE):
        return False

    df = pd.read_parquet(TICKETS_FILE)
    ticket_index = df[df['id'] == ticket_id].index

    if not ticket_index.empty:
        idx = ticket_index[0]

        # garante que a coluna exista e que cada célula tenha sua própria lista
        if 'responses' not in df.columns:
            df['responses'] = pd.Series([[] for _ in range(len(df))], dtype=object)

        # pega valor atual e transforma em lista nova
        responses = df.at[idx, 'responses']
        if isinstance(responses, str):
            try:
                responses = ast.literal_eval(responses)
            except Exception:
                responses = []
        if not isinstance(responses, list):
            responses = list(responses) if hasattr(responses, '__iter__') and not isinstance(responses, (str, bytes)) else []

        new_reply = {
            'text': reply_text,
            'user_email': user_email,
            'timestamp': datetime.now()
        }

        # sempre opere em nova lista (evita referências compartilhadas)
        new_responses = list(responses)  # copia
        new_responses.append(new_reply)

        df.at[idx, 'responses'] = new_responses
        df.to_parquet(TICKETS_FILE, index=False)
        return True

    return False


def create_ticket(title, urgency, sector, description, user_email, attachment=None):
    """Cria um novo chamado e o salva no arquivo Parquet."""
    attachment_path = None
    
    if os.path.exists(TICKETS_FILE):
        df_existing = pd.read_parquet(TICKETS_FILE)
        ticket_id = df_existing['id'].max() + 1 if not df_existing.empty else 1
    else:
        ticket_id = 1
        df_existing = pd.DataFrame()

    if attachment and attachment.filename:
        filename = f"{ticket_id}_{attachment.filename}"
        attachment_path = os.path.join(UPLOAD_FOLDER, filename)
        attachment.save(attachment_path)

    new_ticket = {
        'id': ticket_id,
        'title': title,
        'urgency': urgency,
        'sector': sector,
        'description': description,
        'user_email': user_email,
        'status': 'Aberto',
        'created_at': datetime.now(),
        'attachment': attachment_path,
        'responses': [] 
    }

    df_new = pd.DataFrame([new_ticket])

    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined.to_parquet(TICKETS_FILE, index=False)
    
    return ticket_id

def update_ticket_status(ticket_id, new_status):
    """Atualiza o status de um chamado."""
    if not os.path.exists(TICKETS_FILE):
        return False

    df = pd.read_parquet(TICKETS_FILE)
    ticket_index = df[df['id'] == ticket_id].index

    if not ticket_index.empty:
        idx = ticket_index[0]
        df.at[idx, 'status'] = new_status
        df.to_parquet(TICKETS_FILE, index=False)
        return True
        
    return False