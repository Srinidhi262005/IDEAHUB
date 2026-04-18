import os
from flask import Flask
from Ideahub.extensions import db, migrate, login_manager, socketio, session

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret"

    # ✅ SINGLE SOURCE OF TRUTH
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.abspath(
        os.path.join(BASE_DIR, "..", "instance", "ideahub.db")
    )
    # Move session storage OUT of OneDrive to avoid cloud sync conflicts
    SESSION_PATH = os.path.abspath(os.path.join(os.environ.get("TEMP", "C:\\Temp"), "ideahub_sessions"))
    os.makedirs(SESSION_PATH, exist_ok=True)

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Fix 3: Explicit session configuration for Flask-Login persistence
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = SESSION_PATH
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_NAME'] = 'ideahub_session'

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(app)
    session.init_app(app)

    login_manager.login_view = "routes.login"

    @login_manager.user_loader
    def load_user(user_id):
        from Ideahub.models import User
        try:
            user = User.query.get(int(user_id))
            return user
        except Exception as e:
            print(f"[load_user ERROR] Failed to load user {user_id}: {e}")
            return None

    from Ideahub.routes import routes
    app.register_blueprint(routes)

    from Ideahub.mentors.routes import mentors_bp
    app.register_blueprint(mentors_bp)

    return app


