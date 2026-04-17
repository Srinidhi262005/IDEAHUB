# app.py
from flask import Flask
from flask_login import LoginManager
from models import db, User
from routes import routes   # ✅ Import routes blueprint

app = Flask(__name__)

# Configurations
app.config['SECRET_KEY'] = "your-secret-key"
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///ideahub.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "routes.login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(routes)

# Run app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)






