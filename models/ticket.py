from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    urgency = db.Column(db.String(50), nullable=False)
    sector = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), default='Aberto')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    attachments = db.relationship('Attachment', backref='ticket', lazy=True, cascade="all, delete-orphan")
    responses = db.relationship('Response', backref='ticket', lazy=True, cascade="all, delete-orphan", order_by='Response.timestamp')

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    attachments = db.relationship('Attachment', backref='response', lazy=True, cascade="all, delete-orphan")

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'))
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'))
    filepath = db.Column(db.String(300), nullable=False)
    filename = db.Column(db.String(150), nullable=False)