from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class ProjectStage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    deadline = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='Pendente') # Pendente, Em Andamento, Concluído
    interactions = db.relationship('Interaction', backref='stage', lazy=True)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    urgency = db.Column(db.String(50), nullable=False)
    sector = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), default='Aberto')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    deadline = db.Column(db.DateTime, nullable=True)
    assigned_user_email = db.Column(db.String(120), nullable=True)
    
    ticket_type = db.Column(db.String(50), default='chamado') # chamado ou projeto
    
    attachments = db.relationship('Attachment', backref='ticket', lazy=True, cascade="all, delete-orphan")
    interactions = db.relationship('Interaction', backref='ticket', lazy=True, cascade="all, delete-orphan", 
                                   order_by='Interaction.timestamp',
                                   primaryjoin="Interaction.ticket_id == Ticket.id and Interaction.parent_id == None")
    
    project_stages = db.relationship('ProjectStage', backref='ticket', lazy=True, cascade="all, delete-orphan")
    
    @property
    def completed_stages_count(self):
        return len([s for s in self.project_stages if s.status == 'Concluído'])

    @property
    def total_stages_count(self):
        return len(self.project_stages)

    @property
    def progress(self):
        if self.ticket_type != 'projeto' or not self.project_stages:
            return 0
        return (self.completed_stages_count / self.total_stages_count) * 100 if self.project_stages else 0


class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    action_type = db.Column(db.String(50), nullable=False, default='comment') 
    text = db.Column(db.Text, nullable=True) 
    interaction_data = db.Column(db.JSON, nullable=True)
    
    # NOVOS CAMPOS PARA SUB-TAREFAS E PRAZOS
    deadline = db.Column(db.DateTime, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('interaction.id'), nullable=True)
    
    project_stage_id = db.Column(db.Integer, db.ForeignKey('project_stage.id'), nullable=True)
    
    attachments = db.relationship('Attachment', backref='interaction', lazy=True, cascade="all, delete-orphan")
    children = db.relationship('Interaction', backref=db.backref('parent', remote_side=[id]),
                               lazy=True, cascade="all, delete-orphan")

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'))
    interaction_id = db.Column(db.Integer, db.ForeignKey('interaction.id'))
    filepath = db.Column(db.String(300), nullable=False)
    filename = db.Column(db.String(150), nullable=False)