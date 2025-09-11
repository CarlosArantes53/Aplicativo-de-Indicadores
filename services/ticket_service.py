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
    """Busca um chamado específico pelo seu ID."""
    if not os.path.exists(TICKETS_FILE):
        return None
    
    df = pd.read_parquet(TICKETS_FILE)
    ticket_df = df[df['id'] == ticket_id]
    
    if not ticket_df.empty:
        ticket = ticket_df.to_dict('records')[0]
    
        responses = ticket.get('responses')
        
        if responses is not None and len(responses) > 0:
            for reply in responses:
                if isinstance(reply.get('timestamp'), str):
                    try:
                        reply['timestamp'] = pd.to_datetime(reply['timestamp'])
                    except (ValueError, TypeError):
                        pass
                        
        return ticket
    return None


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

def add_reply_to_ticket(ticket_id, reply_text, user_email):
    if not os.path.exists(TICKETS_FILE):
        return False

    df = pd.read_parquet(TICKETS_FILE)
    ticket_index = df[df['id'] == ticket_id].index

    if not ticket_index.empty:
        idx = ticket_index[0]
        
        if 'responses' not in df.columns:
            df['responses'] = pd.Series([[] for _ in range(len(df))], dtype=object)

        new_reply = {
            'text': reply_text,
            'user_email': user_email,
            'timestamp': datetime.now()
        }
        
        responses = df.at[idx, 'responses']
        if not isinstance(responses, list):
            responses = []
        responses.append(new_reply)
        
        df.at[idx, 'responses'] = responses
        
        df.to_parquet(TICKETS_FILE, index=False)
        return True
        
    return False

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