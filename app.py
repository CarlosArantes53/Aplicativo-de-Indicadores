import os
from flask import Flask, request, url_for, session, flash, redirect
from flask_minify import Minify
from markupsafe import escape, Markup
from models.ticket import db
import re
from urllib.parse import urlencode
from config import auth

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL_DB')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    db.init_app(app)
    app.jinja_env.add_extension('jinja2.ext.do')

    @app.before_request
    def refresh_firebase_token():
        if 'user' in session and 'refreshToken' in session['user']:
            try:
                user_auth_data = auth.refresh(session['user']['refreshToken'])
                
                session['user']['idToken'] = user_auth_data['idToken']
                session['user']['refreshToken'] = user_auth_data['refreshToken']
                session.modified = True 
                
            except Exception as e:
                flash('Sua sessão expirou. Por favor, faça login novamente.', 'warning')
                session.pop('user', None)
                if request.endpoint and 'login' not in request.endpoint and 'static' not in request.endpoint:
                    return redirect(url_for('auth.login'))
                
    def autolink(value):
        if not value:
            return ''
        url_pattern = re.compile(r'((?:https?://|www\.)[^\s<]+[^<.,:;"\'\]\s])')
        html = url_pattern.sub(r'<a href="\1" target="_blank">\1</a>', escape(value))
        return Markup(html)

    def nl2br(value):
        if value is None:
            return ''
        linked_text = autolink(value)
        html = linked_text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br/>')
        return Markup(html)
    
    def url_for_with_query(endpoint, **overrides):
        args = request.args.to_dict(flat=False)
        for k, v in overrides.items():
            args[k] = v if isinstance(v, (list, tuple)) else [v]
        query = urlencode(args, doseq=True)
        base = url_for(endpoint)
        return base + ('?' + query if query else '')

    app.jinja_env.globals['url_for_with_query'] = url_for_with_query

    app.jinja_env.filters['nl2br'] = nl2br
    app.jinja_env.filters['autolink'] = autolink

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