import os
from flask import Flask
from flask_minify import Minify
from markupsafe import escape, Markup

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY')

    # Registrar filtro nl2br seguro para uso nos templates
    def nl2br(value):
        if value is None:
            return ''
        # Primeiro escape para evitar XSS, depois convertemos quebras em <br/>
        # Tratamos \r\n, \r e \n
        escaped = escape(value)
        # substituir por <br/> mantendo segurança
        html = escaped.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br/>')
        return Markup(html)

    app.jinja_env.filters['nl2br'] = nl2br

    if not app.config.get('DEBUG', False):
        Minify(app=app, html=True, js=True, cssless=True)

    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.admin import admin_bp
    from routes.tickets import tickets_bp  # Adicionar esta linha

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(tickets_bp)  # Adicionar esta linha

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
