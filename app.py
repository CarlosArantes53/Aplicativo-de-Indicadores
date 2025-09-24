import os
from flask import Flask
from flask_minify import Minify
from markupsafe import escape, Markup
from models.ticket import db  # Importação do objeto db
import re

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY')
    
    # Configuração do Banco de Dados SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///tickets.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa o banco de dados com o app
    db.init_app(app)

    # --- NOVO FILTRO PARA TRANSFORMAR URLS EM LINKS ---
    def autolink(value):
        if not value:
            return ''
        # Expressão regular para encontrar URLs
        url_pattern = re.compile(r'((?:https?://|www\.)[^\s<]+[^<.,:;"\'\]\s])')
        # Substitui cada URL encontrada por uma tag <a>
        html = url_pattern.sub(r'<a href="\1" target="_blank">\1</a>', escape(value))
        return Markup(html)

    def nl2br(value):
        if value is None:
            return ''
        # Aplica o autolink antes de converter quebras de linha
        linked_text = autolink(value)
        # Converte quebras de linha para <br>
        html = linked_text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br/>')
        return Markup(html)

    app.jinja_env.filters['nl2br'] = nl2br
    # --- FIM DO NOVO FILTRO ---

    if not app.config.get('DEBUG', False):
        Minify(app=app, html=True, js=True, cssless=True)

    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.admin import admin_bp
    from routes.tickets import tickets_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(tickets_bp)

    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)