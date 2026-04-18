from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_session import Session

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# 🚨 FORCE THREADING (NO EVENTLET)
socketio = SocketIO(async_mode="threading")
session = Session()
















