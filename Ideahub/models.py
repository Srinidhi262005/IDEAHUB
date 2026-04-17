# models.py
from Ideahub.extensions import db
from flask_login import UserMixin
from datetime import datetime, date
# ---------------- USER ----------------
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    # ---------- CORE ----------
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # student | faculty | admin

    # ---------- DEPARTMENT (IMPORTANT FIX) ----------
    department_name = db.Column(db.String(100))  
    # examples: "CSE", "CSE AI & ML", "MECHANICAL", "H&S"

    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    department = db.relationship('Department', back_populates='users')

    # ---------- FACULTY INFO ----------
    designation = db.Column(db.String(100))
    qualification = db.Column(db.String(200))

    # ---------- STUDENT INFO ----------
    year = db.Column(db.Integer)
    section = db.Column(db.String(10))

    # ---------- IDEAS ----------
    ideas_submitted = db.relationship(
        'Idea',
        back_populates='student',
        foreign_keys='Idea.user_id',
        lazy='dynamic'
    )

    ideas_mentored = db.relationship(
        'Idea',
        back_populates='mentor',
        foreign_keys='Idea.mentor_id',
        lazy='dynamic'
    )

    # ---------- TEAMS ----------
    teams_led = db.relationship(
        'Team',
        back_populates='leader',
        foreign_keys='Team.leader_id',
        lazy='dynamic'
    )

    teams_member = db.relationship(
        'TeamMember',
        back_populates='user',
        foreign_keys='TeamMember.user_id',
        lazy='dynamic'
    )

    # ---------- NOTIFICATIONS ----------
    notifications = db.relationship(
        'Notification',
        back_populates='user',
        lazy='dynamic'
    )

    # ---------- DOCUMENTS ----------
    documents = db.relationship(
        'Document',
        back_populates='user',
        foreign_keys='Document.user_id',
        lazy='dynamic'
    )

    # ---------- CHAT (CORRECT & FINAL) ----------
    messages_sent = db.relationship(
        'ChatMessage',
        back_populates='sender',
        foreign_keys='ChatMessage.sender_id',
        lazy='dynamic'
    )

    messages_received = db.relationship(
        'ChatMessage',
        back_populates='receiver',
        foreign_keys='ChatMessage.receiver_id',
        lazy='dynamic'
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"



# ---------------- DEPARTMENT ----------------
class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    users = db.relationship(
        'User',
        back_populates='department',
        lazy='dynamic'
    )

    def __repr__(self):
        return f"<Department {self.name}>"



# ---------------- IDEA ----------------
class Idea(db.Model):
    __tablename__ = 'ideas'

    id = db.Column(db.Integer, primary_key=True)

    # ---------------- EXISTING FIELDS ----------------
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    tech_stack = db.Column(db.String(200), nullable=False)
    file = db.Column(db.String(300))
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

    # ---------------- PROJECT FIELDS (ONLY ADDITION) ----------------
    project_type = db.Column(
        db.String(10),
        nullable=True
    )  # 'mini' or 'major'

    academic_year = db.Column(
        db.String(20),
        nullable=True
    )  # e.g. '2022-23', '2023-24'

    # ---------------- RELATIONSHIPS ----------------
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    student = db.relationship(
        'User',
        back_populates='ideas_submitted',
        foreign_keys=[user_id]
    )

    mentor = db.relationship(
        'User',
        back_populates='ideas_mentored',
        foreign_keys=[mentor_id]
    )

    teams = db.relationship(
        'Team',
        back_populates='idea',
        lazy='dynamic'
    )

    def __repr__(self):
        return f"<Idea {self.title} | {self.project_type} | {self.academic_year}>"

    


# ---------------- COLLABORATION REQUEST ---------------

class Collaboration(db.Model):
    __tablename__ = 'collaborations'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    skills_required = db.Column(db.String(200))
    team_size = db.Column(db.Integer)
    deadline = db.Column(db.Date)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', backref='created_collaborations')
    teams = db.relationship('CollaborationTeam', backref='collaboration', lazy=True)
    comments = db.relationship('CollaborationComment', backref='collaboration', lazy=True)


class CollaborationTeam(db.Model):
    __tablename__ = 'collaboration_teams'

    id = db.Column(db.Integer, primary_key=True)
    collaboration_id = db.Column(db.Integer, db.ForeignKey('collaborations.id'))
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    leader = db.relationship('User', backref='led_teams')
    members = db.relationship('CollaborationMember', backref='team', lazy=True)
    requests = db.relationship('CollaborationRequest', backref='team', lazy=True)


class CollaborationMember(db.Model):
    __tablename__ = 'collaboration_members'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('collaboration_teams.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120))
    department = db.Column(db.String(50))
    year = db.Column(db.String(10))
    section = db.Column(db.String(10))


class CollaborationRequest(db.Model):
    __tablename__ = 'collaboration_requests'

    id = db.Column(db.Integer, primary_key=True)
    collaboration_id = db.Column(db.Integer, db.ForeignKey('collaborations.id'))
    team_id = db.Column(db.Integer, db.ForeignKey('collaboration_teams.id'), nullable=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='Pending')   # Pending / Accepted / Rejected
    date_requested = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 🔥 NEW: Track when the request was accepted/rejected
    date_updated = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])


class CollaborationComment(db.Model):
    __tablename__ = 'collaboration_comments'

    id = db.Column(db.Integer, primary_key=True)
    collaboration_id = db.Column(db.Integer, db.ForeignKey('collaborations.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text, nullable=False)
    file_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='collab_comments')




# ---------------- EVENT (Generic campus events) ----------------
class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False)  # hackathon / technical / sports / cultural / other
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(150))
    organizer = db.Column(db.String(150))
    poster = db.Column(db.String(300))
    cta_link = db.Column(db.String(300))

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by])

    @property
    def status(self):
        today = date.today()
        if self.start_date and self.end_date:
            if self.start_date <= today <= self.end_date:
                return "ONGOING"
            if today < self.start_date:
                return "UPCOMING"
        return "PAST"


# ---------------- HACKATHON ----------------

class Hackathon(db.Model):
    __tablename__ = 'hackathons'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reg_deadline = db.Column(db.Date, nullable=True)

    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    theme = db.Column(db.String(50))
    poster = db.Column(db.String(300))
    prize = db.Column(db.String(100))

    # ✅ ADD THESE TWO LINES
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_role = db.Column(db.String(20))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teams = db.relationship('Team', back_populates='hackathon', lazy='dynamic')

    @property
    def status(self):
        today = datetime.utcnow().date()
        if today < self.start_date:
            return "UPCOMING"
        elif self.start_date <= today <= self.end_date:
            return "ONGOING"
        return "ENDED"

    # Backwards-compatibility: some templates (older) expect `event.date`.
    @property
    def date(self):
        """Return the primary date for the event (start_date) so
        templates that call `event.date.strftime(...)` continue to work.
        """
        return self.start_date

    # Relationship so templates can use `event.department.name` safely
    department = db.relationship('Department', backref='hackathons', lazy='joined')

# ---------------- TEAM ----------------
class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hackathon_id = db.Column(db.Integer, db.ForeignKey('hackathons.id'), nullable=True)
    idea_id = db.Column(db.Integer, db.ForeignKey('ideas.id'), nullable=True)
    idea_name = db.Column(db.String(250))
    section = db.Column(db.String(20))
    year = db.Column(db.String(10))
    department = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    leader = db.relationship('User', back_populates='teams_led', foreign_keys=[leader_id])
    hackathon = db.relationship('Hackathon', back_populates='teams')
    idea = db.relationship('Idea', back_populates='teams')
    members = db.relationship('TeamMember', back_populates='team', lazy='dynamic')
    def __repr__(self):
        return f"<Team {self.name}>"

# ---------------- TEAM MEMBER ----------------
class TeamMember(db.Model):
    __tablename__ = 'team_members'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(150), nullable=False)
    section = db.Column(db.String(10))
    year = db.Column(db.String(10))
    department = db.Column(db.String(50))
    email = db.Column(db.String(120)) 
    team = db.relationship('Team', back_populates='members', foreign_keys=[team_id])
    user = db.relationship('User', back_populates='teams_member', foreign_keys=[user_id])
    def __repr__(self):
        return f"<TeamMember {self.name} in team {self.team_id}>"

# ---------------- CHAT MESSAGE ----------------
class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])


# ---------------- NOTIFICATION ----------------
class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    title = db.Column(db.String(100))        # short
    message = db.Column(db.String(255))      # readable text

    module = db.Column(db.String(50))        # chat / team / hackathon / collab
    ref_id = db.Column(db.Integer)            # related object id

    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # <-- ADDED: explicit relationship so back_populates on User works
    user = db.relationship('User', back_populates='notifications', foreign_keys=[user_id])


# ---------------- DOCUMENT ----------------
class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='documents', foreign_keys=[user_id])

class Mentor(db.Model):
    __tablename__ = 'mentors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    qualification = db.Column(db.String(150), nullable=True)
    designation = db.Column(db.String(150), nullable=True)

    def __repr__(self):
        return f"<Mentor {self.name}>"


class Score(db.Model):
    __tablename__ = 'scores'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    mentor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    hackathon_id = db.Column(db.Integer, db.ForeignKey('hackathons.id'))
    score = db.Column(db.Integer)



# ---------------- INDEXES ----------------
db.Index('ix_user_email', User.email)
db.Index('ix_idea_title', Idea.title)


def create_all_tables():
    from Ideahub import create_app
    app = create_app()
    with app.app_context():
        db.create_all()
        print("✅ All tables created successfully!")

