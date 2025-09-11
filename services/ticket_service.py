import pandas as pd
import os
from datetime import datetime
import uuid

TICKETS_FILE = 'tickets.parquet'
UPLOAD_FOLDER = 'uploads/tickets'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
    ticket = df[df['id'] == ticket_id]
    
    if not ticket.empty:
        return ticket.to_dict('records')[0]
    return None


def create_ticket(title, urgency, sector, description, user_email, attachment=None):
    """Cria um novo chamado e o salva no arquivo Parquet."""
    ticket_id = str(uuid.uuid4())
    attachment_path = None

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

    if os.path.exists(TICKETS_FILE):
        df_existing = pd.read_parquet(TICKETS_FILE)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_parquet(TICKETS_FILE, index=False)
    return ticket_id

def add_reply_to_ticket(ticket_id, reply_text, user_email):
    if not os.path.exists(TICKETS_FILE):
        return False

    df = pd.read_parquet(TICKETS_FILE)
    ticket_index = df[df['id'] == ticket_id].index

    if not ticket_index.empty:
        idx = ticket_index[0]
        
        # Assegura que a coluna 'responses' exista e seja do tipo objeto
        if 'responses' not in df.columns:
            df['responses'] = pd.Series([[] for _ in range(len(df))], dtype=object)

        # Adiciona a nova resposta
        new_reply = {
            'text': reply_text,
            'user_email': user_email,
            'timestamp': datetime.now()
        }
        
        # Recupera a lista de respostas e adiciona a nova
        responses = df.at[idx, 'responses']
        if not isinstance(responses, list):
            responses = [] # Inicializa como lista se não for
        responses.append(new_reply)
        
        # Atualiza o DataFrame
        df.at[idx, 'responses'] = responses
        
        # Salva as alterações
        df.to_parquet(TICKETS_FILE, index=False)
        return True
        
    return False