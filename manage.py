from Ideahub import create_app
from Ideahub.extensions import db
from Ideahub.models import User, Department, Idea, CollaborationRequest, Hackathon, Team, TeamMember, ChatMessage, Notification, Document, Mentor
from flask_migrate import Migrate
from flask.cli import FlaskGroup

# ---------------- CREATE APP ----------------
app = create_app()

# ---------------- MIGRATE ----------------
migrate = Migrate(app, db)  # Important for db commands

# ---------------- CLI ----------------
cli = FlaskGroup(app)

@app.shell_context_processor
def make_shell_context():
    return dict(
        app=app,
        db=db,
        User=User,
        Department=Department,
        Idea=Idea,
        CollaborationRequest=CollaborationRequest,
        Hackathon=Hackathon,
        Team=Team,
        TeamMember=TeamMember,
        ChatMessage=ChatMessage,
        Notification=Notification,
        Document=Document,
        Mentor=Mentor,
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    cli()




