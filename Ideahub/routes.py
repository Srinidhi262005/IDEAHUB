from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, current_app, send_file, abort,
    send_from_directory
)

from flask_login import (
    login_required, current_user,
    login_user, logout_user
)

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app

from sqlalchemy import or_
from datetime import datetime, date
import os
# ---------------- DATABASE ----------------
from Ideahub.extensions import db

# ---------------- MODELS ----------------
from Ideahub.models import (
    User,
    Department,
    Mentor,
    Idea,
    Hackathon,
    Event,
    Team,
    TeamMember,
    Collaboration,
    CollaborationRequest,
    CollaborationTeam,
    CollaborationMember,
    CollaborationComment,
    Document,
    Notification,
    ChatMessage
)


routes = Blueprint("routes", __name__)

EVENT_CATEGORIES = [
    ("all", "All"),
    ("hackathon", "Hackathon"),
    ("technical", "Technical"),
    ("sports", "Sports"),
    ("cultural", "Cultural"),
    ("workshop", "Workshop"),
    ("other", "Other")
]



# ---------------- CONFIG ----------------

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt", "xlsx", "pptx", "jpg", "jpeg", "png"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_folder_abs():
    # Absolute path to uploads folder inside current Flask app
    return os.path.join(current_app.root_path, 'static', 'uploads')

def event_upload_abs():
    return os.path.join(current_app.root_path, 'static', 'uploads', 'events')


# Serve project-level `images/` directory at the path templates expect.
# Many templates reference `url_for('static', filename='images/XYZ')` but the
# image assets live in a repo-level `images/` folder — map those requests
# and provide a safe fallback when an asset is missing.
@routes.route('/static/images/<path:filename>')
def _serve_repo_images(filename):
    # Images actually live one level above the Flask package
    images_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'images'))

    # Map commonly referenced but missing assets to existing ones
    aliases = {
        "campus_bg.jpg": "college_front.png",
        "student_bg.jpg": "college_front.png",
        "bg_shapes.png": "bg1.png",
        "login-bg.jpg": "hero-background.png",
        "register-bg.jpg": "hero-background.png",
    }

    candidate = os.path.join(images_dir, filename)
    if os.path.exists(candidate):
        return send_from_directory(images_dir, filename)

    alt = aliases.get(filename)
    if alt:
        alt_path = os.path.join(images_dir, alt)
        if os.path.exists(alt_path):
            return send_from_directory(images_dir, alt)

    # fallback to a safe, existing site asset
    return send_from_directory(images_dir, 'jits_logo.png')


@routes.route('/favicon.ico')
def _favicon():
    images_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'images'))
    ico = os.path.join(images_dir, 'favicon.ico')
    if os.path.exists(ico) and os.path.getsize(ico) > 0:
        return send_from_directory(images_dir, 'favicon.ico')
    # fall back to a visible icon if .ico is empty/missing
    return send_from_directory(images_dir, 'jits_logo.png')


# Serve uploads from multiple locations (root static/uploads or mentors static/uploads)
@routes.route('/static/uploads/<path:filename>')
def _serve_uploads(filename):
    # 1) prefer app static/uploads
    p1 = os.path.join(current_app.root_path, 'static', 'uploads', filename)
    if os.path.exists(p1):
        return send_from_directory(os.path.join(current_app.root_path, 'static', 'uploads'), filename)

    # 2) fall back to mentor-specific uploads folder (legacy layout)
    p2_base = os.path.join(current_app.root_path, 'Ideahub', 'mentors', 'static', 'uploads')
    p2 = os.path.join(p2_base, filename)
    if os.path.exists(p2):
        return send_from_directory(p2_base, filename)

    # Final fallback — return a small existing image so pages don't break visually
    images_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'images'))
    return send_from_directory(images_dir, 'jits_logo.png')

# ---------------- HOME ----------------
@routes.route('/')
def home():
    events = Hackathon.query \
        .order_by(Hackathon.start_date.desc()) \
        .limit(4) \
        .all()

    mentors = Mentor.query \
        .order_by(Mentor.name) \
        .limit(6) \
        .all()

    return render_template(
        'index.html',
        events=events,
        mentors=mentors
    )


@routes.route('/events', methods=['GET', 'POST'])
def events_view():
    today = date.today()
    filter_category = request.args.get('category', 'all').lower()
    filter_status = request.args.get('status', '').lower()

    query = Event.query.filter(Event.end_date >= today)

    if filter_category and filter_category != 'all':
        query = query.filter(Event.category == filter_category)

    if filter_status == 'ongoing':
        query = query.filter(Event.start_date <= today, Event.end_date >= today)
    elif filter_status == 'upcoming':
        query = query.filter(Event.start_date > today)

    events = query.order_by(Event.start_date.asc()).all()

    can_manage = current_user.is_authenticated and current_user.role in ['admin', 'mentor']

    if request.method == 'POST':
        if not can_manage:
            flash("Only mentors or admins can publish events.", "danger")
            return redirect(url_for('routes.login'))

        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'other').lower()
        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        location = request.form.get('location', '').strip()
        organizer = request.form.get('organizer', '').strip()
        cta_link = request.form.get('cta_link', '').strip()

        if not title or not description or not start_date_str or not end_date_str:
            flash("Title, description, start date and end date are required.", "danger")
            return redirect(url_for('routes.events_view'))

        try:
            sd = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            ed = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "danger")
            return redirect(url_for('routes.events_view'))

        if ed < sd:
            flash("End date cannot be before start date.", "danger")
            return redirect(url_for('routes.events_view'))

        poster_file = request.files.get('poster')
        poster_path = None
        if poster_file and poster_file.filename.strip():
            if allowed_file(poster_file.filename):
                safe_name = f"{int(datetime.utcnow().timestamp())}_{secure_filename(poster_file.filename)}"
                dest_dir = event_upload_abs()
                os.makedirs(dest_dir, exist_ok=True)
                poster_file.save(os.path.join(dest_dir, safe_name))
                poster_path = f"events/{safe_name}"
            else:
                flash("Poster must be an accepted file type.", "danger")
                return redirect(url_for('routes.events_view'))

        event = Event(
            title=title,
            description=description,
            category=category,
            start_date=sd,
            end_date=ed,
            location=location or None,
            organizer=organizer or None,
            poster=poster_path,
            cta_link=cta_link or None,
            created_by=current_user.id
        )

        db.session.add(event)
        db.session.commit()
        flash("Event published.", "success")
        return redirect(url_for('routes.events_view'))

    category_labels = {k: v for k, v in EVENT_CATEGORIES}

    return render_template(
        'events.html',
        events=events,
        categories=EVENT_CATEGORIES,
        filter_category=filter_category,
        filter_status=filter_status,
        category_labels=category_labels,
        can_manage=can_manage,
        today=today,
        featured_posters=[
            {
                "title": "INNOFEST 2026",
                "subtitle": "Intercollegiate Technical Events",
                "dates": "11-12 Feb 2026",
                "deadline": "Last date: 09 Feb 2026",
                "poster": "events/innofest-tech.jpg",
                "tone": "tech"
            },
            {
                "title": "INNOFEST 2026",
                "subtitle": "Inaugural Function",
                "dates": "12 Feb 2026",
                "deadline": "Be there!",
                "poster": "events/innofest-inaugural.jpg",
                "tone": "tech"
            },
            {
                "title": "RADIANCE 2026",
                "subtitle": "Cultural & Literary Events",
                "dates": "11-12 Feb 2026",
                "deadline": "Last date: 09 Feb 2026",
                "poster": "events/radiance-2026.jpg",
                "tone": "culture"
            },
            {
                "title": "SPORTSFESTA 2026",
                "subtitle": "Sports & Games Meet",
                "dates": "Feb 2026",
                "deadline": "Register early",
                "poster": "events/sportsfesta.jpg",
                "tone": "sports"
            }
        ]
    )


# ---------------- ABOUT US ----------------
@routes.route('/about')
def about_us():
    return render_template('about_us.html')

# ---------------- REGISTER ----------------
@routes.route('/register', methods=['GET','POST'])
def register():
    try:
        departments = Department.query.order_by(Department.name).all()
    except:
        departments = []
        flash("Database not ready. Run migrations!", "danger")

    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password')
        role = request.form.get('role','student')
        department_id = request.form.get('department_id') or None
        
        # Student specific
        year = request.form.get('year')
        section = request.form.get('section')
        # Faculty specific
        qualification = request.form.get('qualification')

        if not name or not email or not password:
            flash("All fields required", "danger")
            return redirect(url_for('routes.register'))

        if User.query.filter_by(email=email).first():
            flash("Email already exists!", "danger")
            return redirect(url_for('routes.register'))

        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=role,
            department_id=int(department_id) if department_id else None,
            year=int(year) if year and year.isdigit() else None,
            section=section,
            qualification=qualification
        )
        db.session.add(user)
        db.session.commit()
        flash("Registration successful!", "success")
        return redirect(url_for('routes.login'))

    return render_template('register.html', departments=departments)

# ---------------- LOGIN ----------------

@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)

            print("AFTER login_user → authenticated =", current_user.is_authenticated)

            return redirect(url_for('routes.dashboard'))

        flash("Invalid credentials!", "danger")

    return render_template('login.html')





# ---------------- LOGOUT ----------------
@routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for('routes.login'))

@routes.route('/dashboard')
@login_required
def dashboard():
    # Only show current user's ideas
    my_ideas = Idea.query.filter_by(user_id=current_user.id).order_by(Idea.date_posted.desc()).all()
    hackathons = Hackathon.query.order_by(Hackathon.start_date.desc()).all()
    collab_requests = CollaborationRequest.query.filter_by(receiver_id=current_user.id).all()
    # FIX: use created_at (Notification.timestamp does not exist)
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()

    # Teams where user is leader or member
    teams = Team.query.outerjoin(TeamMember).filter(
        or_(Team.leader_id == current_user.id, TeamMember.user_id == current_user.id)
    ).all()

    documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.upload_date.desc()).all()

    # Combine recent activity
    recent_activity = []
    for idea in my_ideas:
        recent_activity.append({'message': f"Submitted idea: {idea.title}", 'date': idea.date_posted})
    for doc in documents:
        recent_activity.append({'message': f"Uploaded document: {doc.filename}", 'date': doc.upload_date})
    recent_activity.sort(key=lambda x: x['date'], reverse=True)

    # ✅ Render dashboard page
    return render_template(
        'dashboard.html',
        ideas=my_ideas,
        hackathons=hackathons,
        collab_requests=collab_requests,
        notifications=notifications,
        teams=teams,
        documents=documents,
        recent_activity=recent_activity,
        current_user=current_user
    )

# ---------------- ADMIN: IMPORT PROJECTS (WEB UPLOAD) ----------------
@routes.route('/admin/import-projects', methods=['GET', 'POST'])
@login_required
def admin_import_projects():
    # Only admins allowed
    if current_user.role != 'admin':
        flash('Admin access only', 'danger')
        return redirect(url_for('routes.dashboard'))

    from Ideahub.pdf_importer import (
        extract_entries_from_pdf, normalize_title, choose_titles_from_lines
    )

    preview_rows = None

    if request.method == 'POST':
        uploaded = request.files.get('pdf')
        if not uploaded or uploaded.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('routes.admin_import_projects'))

        # allow only pdf
        if not uploaded.filename.lower().endswith('.pdf'):
            flash('Please upload a PDF file', 'danger')
            return redirect(url_for('routes.admin_import_projects'))

        filename = secure_filename(uploaded.filename)
        data_dir = os.path.join(current_app.root_path, 'data')
        os.makedirs(data_dir, exist_ok=True)
        save_path = os.path.join(data_dir, filename)
        uploaded.save(save_path)

        if 'preview' in request.form:
            entries = extract_entries_from_pdf(save_path)
            preview_rows = []
            for e in entries:
                if e.get('is_table'):
                    row = e.get('row') or []
                    row_cells = [str(c).strip() for c in row if c and str(c).strip()]
                    preview_rows.append(' | '.join(row_cells))
                else:
                    preview_rows.append(normalize_title(e.get('title') or ''))
            return render_template('admin_import.html', preview=preview_rows[:50], filename=filename)

        # Perform actual import
        year = request.form.get('year')
        ptype = request.form.get('type')
        entries = extract_entries_from_pdf(save_path)

        # find or create admin user to own imports
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user:
            admin_user = User(name='Admin (import)', email='admin-import@local', password=generate_password_hash('ChangeMe123!'), role='admin')
            db.session.add(admin_user)
            db.session.commit()

        created = 0
        table_entries = [e for e in entries if e.get('is_table')]
        text_entries = [e for e in entries if not e.get('is_table')]

        for e in table_entries:
            raw_title = e.get('title') or ''
            row = e.get('row') or []
            title = (raw_title or '').strip()
            if not title or len(title) < 4:
                continue
            row_cells = [str(c).strip() for c in row if c and str(c).strip()]
            description = ' | '.join(row_cells)
            exists = Idea.query.filter(Idea.title == title).first()
            if exists:
                continue
            idea = Idea(title=title[:200], description=f"Imported from PDF row: {description}", tech_stack='', file=None, user_id=admin_user.id, mentor_id=None, project_type=ptype, academic_year=year)
            db.session.add(idea)
            created += 1

        text_lines = [t.get('title') for t in text_entries]
        titles = choose_titles_from_lines(text_lines)
        for raw in titles:
            title = normalize_title(raw)
            if len(title) < 8:
                continue
            exists = Idea.query.filter(Idea.title == title).first()
            if exists:
                continue
            idea = Idea(title=title[:200], description=f"Imported project title from PDF: {filename}", tech_stack='', file=None, user_id=admin_user.id, mentor_id=None, project_type=ptype, academic_year=year)
            db.session.add(idea)
            created += 1

        db.session.commit()
        flash(f'Imported {created} ideas from {filename}', 'success')
        return redirect(url_for('routes.dashboard'))

    return render_template('admin_import.html', preview=preview_rows)

@routes.route('/explore')
def explore():
    projects = (
        Idea.query
        .filter(Idea.academic_year.isnot(None))
        .order_by(Idea.date_posted.desc())
        .all()
    )

    return render_template(
        'explore.html',
        projects=projects
    )

# ---------------- NOTIFICATIONS ----------------
@routes.route('/notifications')
@login_required
def notifications_view():
    # FIX: use created_at
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifs)

@routes.route('/mark_read/<int:notif_id>', methods=['POST'])
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        flash("Unauthorized!", "danger")
        return redirect(url_for('routes.notifications_view'))
    notif.is_read = True
    db.session.commit()
    return redirect(url_for('routes.notifications_view'))

@routes.route('/mark_all_read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for('routes.notifications_view'))


# ---------------- IDEA CRUD ----------------
@routes.route('/submit_idea', methods=['GET','POST'])
@login_required
def submit_idea():
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        tech_stack = request.form.get('tech_stack','').strip()
        project_type = request.form.get('project_type', 'idea')
        academic_year = request.form.get('academic_year', '')

        file = request.files.get('file')
        filename = None

        if file and allowed_file(file.filename):
            filename = f"{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
            abs_folder = upload_folder_abs()
            os.makedirs(abs_folder, exist_ok=True)
            save_path = os.path.join(abs_folder, filename)
            file.save(save_path)

        idea = Idea(
            title=title,
            description=description,
            tech_stack=tech_stack,
            file=filename,
            user_id=current_user.id,
            project_type=project_type,
            academic_year=academic_year
        )

        db.session.add(idea)
        db.session.commit()

        flash("Idea submitted!", "success")
        return redirect(url_for('routes.dashboard'))

    user_ideas = Idea.query.filter_by(user_id=current_user.id).order_by(Idea.date_posted.desc()).all()
    # List of years for the dropdown if needed, or just let users type
    years = [f"{y}-{str(y+1)[2:]}" for y in range(2020, 2026)]
    return render_template('submit_idea.html', user_ideas=user_ideas, years=years)

# ---------------- PROJECTS BY TYPE AND YEAR ----------------


@routes.route("/projects/<string:proj_type>")
def projects_years(proj_type):
    proj_type = proj_type.lower()
    if proj_type not in ["mini", "major"]:
        abort(404)

    years = (
        db.session.query(Idea.academic_year)
        .filter(Idea.project_type == proj_type)
        .distinct()
        .order_by(Idea.academic_year.desc())
        .all()
    )

    years = [y[0] for y in years if y[0]]

    label = "Industry Oriented Mini Projects" if proj_type == "mini" else "Major Projects"

    return render_template(
        "projects_years.html",
        years=years,
        proj_type=proj_type,
        label=label
    )


@routes.route("/projects/<string:proj_type>/<string:year>")
def projects_list(proj_type, year):
    proj_type = proj_type.lower()
    if proj_type not in ["mini", "major"]:
        abort(404)

    projects = (
        Idea.query
        .filter_by(project_type=proj_type, academic_year=year)
        .order_by(Idea.date_posted.desc())
        .all()
    )

    label = "Mini Projects" if proj_type == "mini" else "Major Projects"

    return render_template(
        "projects_list.html",
        projects=projects,
        year=year,
        label=label,
        proj_type=proj_type
    )



@routes.route('/edit_idea/<int:idea_id>', methods=['GET','POST'])
@login_required
def edit_idea(idea_id):
    idea = Idea.query.get_or_404(idea_id)
    if idea.user_id != current_user.id:
        flash("Unauthorized!", "danger")
        return redirect(url_for('routes.dashboard'))
    if request.method=='POST':
        idea.title = request.form.get('title', idea.title)
        idea.description = request.form.get('description', idea.description)
        idea.tech_stack = request.form.get('tech_stack', idea.tech_stack)
        file = request.files.get('file')
        if file and allowed_file(file.filename):
            filename = f"{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
            file_path = os.path.join(upload_folder_abs(), filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)
            idea.file = file_path
        db.session.commit()
        flash("Idea updated!", "success")
        return redirect(url_for('routes.dashboard'))
    return render_template('submit_idea.html', idea=idea, edit=True)


@routes.route('/view_idea/<int:idea_id>')
@login_required
def view_idea(idea_id):
    return redirect(url_for('routes.edit_idea', idea_id=idea_id))

@routes.route('/delete_idea/<int:idea_id>', methods=['POST'])
@login_required
def delete_idea(idea_id):
    idea = Idea.query.get_or_404(idea_id)
    if idea.user_id != current_user.id:
        flash("Unauthorized!", "danger")
        return redirect(url_for('routes.dashboard'))
    db.session.delete(idea)
    db.session.commit()
    flash("Idea deleted!", "info")
    return redirect(url_for('routes.dashboard'))

# ---------------- COLLABORATION REQUESTS ----------------


@routes.route('/collaborations', methods=['GET', 'POST'])
@login_required
def collaborations_view():

    # ---------------- CREATE NEW COLLAB ----------------
    if request.method == 'POST':

        title = request.form.get('title')
        description = request.form.get('description')
        skills_required = request.form.get('skills_required')
        team_size = request.form.get('team_size', 4)
        deadline_str = request.form.get('deadline')

        if not title or not description or not deadline_str:
            flash("Please fill all required fields!", "danger")
            return redirect(url_for('routes.collaborations_view'))

        # Validate team size
        try:
            team_size = int(team_size)
        except ValueError:
            team_size = 4

        # Validate deadline
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid deadline format!", "danger")
            return redirect(url_for('routes.collaborations_view'))

        # Save new collaboration
        collab = Collaboration(
            title=title,
            description=description,
            skills_required=skills_required,
            team_size=team_size,
            deadline=deadline,
            created_by=current_user.id,
            created_at=datetime.utcnow()
        )
        db.session.add(collab)
        db.session.commit()

        flash("Collaboration created successfully!", "success")
        return redirect(url_for('routes.collaborations_view'))

    # ---------------- FETCH ALL COLLABORATIONS ----------------
    collaborations = Collaboration.query.order_by(
        Collaboration.created_at.desc()
    ).all()

    # ---------------- SENT REQUESTS (notifications) ------------
    sent_requests = CollaborationRequest.query.filter_by(
        sender_id=current_user.id
    ).order_by(CollaborationRequest.date_requested.desc()).all()

    # ---------------- RECEIVED REQUESTS (for creators) ---------
    requests_received = CollaborationRequest.query.filter_by(
        receiver_id=current_user.id
    ).order_by(CollaborationRequest.date_requested.desc()).all()

    return render_template(
        'collaboration_requests.html',
        collaborations=collaborations,
        request_status=sent_requests,
        requests=requests_received
    )


# ============================================================
# 2️⃣ SEND COLLABORATION REQUEST  (POST ONLY)
# ============================================================
@routes.route('/send_collaboration_request', methods=['POST'])
@login_required
def send_collaboration_request():

    # prevent GET request
    if request.method != "POST":
        abort(405)

    collab_id = request.form.get('collaboration_id')
    receiver_id = request.form.get('receiver_id')

    if not collab_id or not receiver_id:
        flash("Missing data!", "danger")
        return redirect(url_for('routes.collaborations_view'))

    # Prevent user sending multiple requests for same collab
    existing = CollaborationRequest.query.filter_by(
        collaboration_id=collab_id,
        sender_id=current_user.id
    ).first()

    if existing:
        flash("You have already requested to join this collaboration.", "info")
        return redirect(url_for('routes.collaborations_view'))

    cr = CollaborationRequest(
        collaboration_id=int(collab_id),
        sender_id=current_user.id,
        receiver_id=int(receiver_id),
        status='Pending',
        date_requested=datetime.utcnow()
    )

    db.session.add(cr)
    db.session.commit()

    flash("Collaboration request sent!", "success")
    return redirect(url_for('routes.collaborations_view'))


# ============================================================
# 3️⃣ ACCEPT OR REJECT COLLAB REQUEST
# ============================================================
@routes.route('/manage_collaboration/<int:request_id>/<action>')
@login_required
def manage_collaboration(request_id, action):

    cr = CollaborationRequest.query.get_or_404(request_id)

    # Only receiver can accept or reject
    if current_user.id != cr.receiver_id:
        flash("Unauthorized!", "danger")
        return redirect(url_for('routes.collaborations_view'))

    # ---------------- ACCEPT ----------------
    if action.lower() == 'accept':
        cr.status = 'Accepted'

        # Check if team already exists
        team = cr.team

        if not team:
            collab = cr.collaboration
            team_name = f"Team_{cr.sender_id}_{int(datetime.utcnow().timestamp())}"

            team = CollaborationTeam(
                collaboration_id=collab.id,
                leader_id=current_user.id,
                name=team_name,
                status="Active",
                created_at=datetime.utcnow()
            )

            db.session.add(team)
            db.session.commit()

            # Assign team ID to request
            cr.team_id = team.id

        # Add member to team
        member = CollaborationMember(
            team_id=team.id,
            user_id=cr.sender.id,
            name=cr.sender.name,
            email=cr.sender.email,
            department=cr.sender.department_name,
            year=cr.sender.year,
            section=cr.sender.section
        )

        db.session.add(member)
        db.session.commit()

        flash("Request accepted!", "success")

    # ---------------- REJECT ----------------
    elif action.lower() == 'reject':
        cr.status = 'Rejected'
        db.session.commit()
        flash("Request rejected!", "info")

    return redirect(url_for('routes.collaborations_view'))


# ============================================================
# 4️⃣ ADD COMMENT WITH OPTIONAL FILE
# ============================================================
@routes.route('/add_collab_comment/<int:collab_id>', methods=['POST'])
@login_required
def add_collab_comment(collab_id):

    collab = Collaboration.query.get_or_404(collab_id)
    content = request.form.get('content')
    file = request.files.get('file')

    if not content:
        flash("Comment cannot be empty!", "danger")
        return redirect(url_for('routes.collaborations_view'))

    file_url = None

    # ------------- File Upload -------------
    if file and file.filename.strip() != "":
        upload_folder = os.path.join('app', 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        filename = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
        file.save(os.path.join(upload_folder, filename))

        file_url = filename

    # ------------- Save Comment ------------
    comment = CollaborationComment(
        collaboration_id=collab.id,
        user_id=current_user.id,
        content=content,
        file_url=file_url,
        created_at=datetime.utcnow()
    )

    db.session.add(comment)
    db.session.commit()

    flash("Comment added!", "success")
    return redirect(url_for('routes.collaborations_view'))

# -------------------------------------------
# HACKATHON MODULE ROUTES (FULL WORKING)
# -------------------------------------------

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from Ideahub.extensions import db
from Ideahub.models import Hackathon, Team, TeamMember, User, Score
from Ideahub.routes import routes


# ---------------------------------------------------------
# CREATE + VIEW HACKATHONS
# ---------------------------------------------------------
@routes.route('/hackathons', methods=['GET', 'POST'])
@login_required
def hackathons_view():

    # ---------------- CREATE HACKATHON ----------------
    if request.method == 'POST':

        new_event = Hackathon(
            title=request.form['title'],
            description=request.form['description'],
            theme=request.form.get('theme'),
            prize=request.form.get('prize'),
            poster=request.form.get('poster'),
            department_id=request.form.get('department_id') or None,
            start_date=datetime.strptime(request.form['start_date'], "%Y-%m-%d").date(),
            end_date=datetime.strptime(request.form['end_date'], "%Y-%m-%d").date(),
            created_by=current_user.id,
            created_role=current_user.role
        )

        db.session.add(new_event)
        db.session.commit()

        flash("Hackathon created successfully!", "success")
        return redirect(url_for('routes.hackathons_view'))

    # ---------------- LIST EVENTS ----------------
    hackathons = Hackathon.query.order_by(Hackathon.start_date.desc()).all()

    return render_template(
        'hackathons.html',
        hackathons=hackathons,
        date_today=date.today()
    )
@routes.route('/register_hackathon/<int:event_id>', methods=['POST'])
@login_required
def register_hackathon(event_id):

    hackathon = Hackathon.query.get_or_404(event_id)

    if hackathon.start_date < date.today():
        flash("Registration closed!", "danger")
        return redirect(url_for('routes.hackathons_view'))

    # Prevent multiple teams
    existing = Team.query.filter_by(
        hackathon_id=event_id,
        leader_id=current_user.id
    ).first()

    if existing:
        flash("You already registered a team!", "warning")
        return redirect(url_for('routes.hackathons_view'))

    team = Team(
        name=request.form['team_name'],
        leader_id=current_user.id,
        hackathon_id=event_id,
        status="Active",
        created_at=datetime.utcnow()
    )

    db.session.add(team)
    db.session.commit()

    leader = TeamMember(
        team_id=team.id,
        user_id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        department=current_user.department_name,
        year=current_user.year,
        section=current_user.section
    )

    db.session.add(leader)
    db.session.commit()

    flash("Team registered successfully!", "success")
    return redirect(url_for('routes.hackathons_view'))

@routes.route('/hackathon/team/manage/<int:team_id>', methods=['POST'])
@login_required
def manage_team(team_id):

    team = Team.query.get_or_404(team_id)

    if current_user.id != team.leader_id:
        abort(403)

    if team.hackathon.start_date <= date.today():
        flash("Cannot add members after event start!", "warning")
        return redirect(url_for('routes.hackathons_view'))

    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()

    if not user:
        flash("User not found!", "danger")
        return redirect(url_for('routes.hackathons_view'))

    if TeamMember.query.filter_by(team_id=team_id, user_id=user.id).first():
        flash("User already in team!", "warning")
        return redirect(url_for('routes.hackathons_view'))

    member = TeamMember(
        team_id=team.id,
        user_id=user.id,
        name=user.name,
        email=user.email,
        department=user.department_name,
        year=user.year,
        section=user.section
    )

    db.session.add(member)
    db.session.commit()

    flash(f"{user.name} added successfully!", "success")
    return redirect(url_for('routes.hackathons_view'))

# ---------------------------------------------------------
# SUBMIT IDEA (Only team members)
# ---------------------------------------------------------
@routes.route('/hackathon/<int:event_id>/submit_idea/<int:team_id>', methods=['POST'])
@login_required
def hackathon_submit_idea(event_id, team_id):
    team = Team.query.get_or_404(team_id)

    # Validate membership
    if current_user.id not in [m.user_id for m in team.members]:
        flash("You are not in this team!", "danger")
        return redirect(url_for('routes.hackathons_view'))

    # Only allowed during event
    today = datetime.utcnow().date()
    if not (team.hackathon.start_date <= today <= team.hackathon.end_date):
        flash("Idea submission closed!", "danger")
        return redirect(url_for('routes.hackathons_view'))

    idea_text = request.form.get('idea')

    team.idea = idea_text
    db.session.commit()

    flash("Idea saved successfully!", "success")
    return redirect(url_for('routes.hackathons_view'))


# ---------------------------------------------------------
# FINAL SUBMISSION (After Event)
# ---------------------------------------------------------
@routes.route('/hackathon/final/<int:team_id>', methods=['POST'])
@login_required
def final_submission(team_id):
    team = Team.query.get_or_404(team_id)

    if current_user.id not in [m.user_id for m in team.members]:
        flash("You do not belong to this team!", "danger")
        return redirect(url_for('routes.hackathons_view'))

    # Only after end_date
    if datetime.utcnow().date() <= team.hackathon.end_date:
        flash("Final submission only after event ends!", "danger")
        return redirect(url_for('routes.hackathons_view'))

    final_link = request.form.get('final_link')
    team.final_link = final_link
    team.submitted_at = datetime.utcnow()

    db.session.commit()

    flash("Final submission successful!", "success")
    return redirect(url_for('routes.hackathons_view'))


# ---------------------------------------------------------
# JUDGE SCORE (Mentor/Admin)
# ---------------------------------------------------------
@routes.route('/hackathon/judge/<int:team_id>/<int:event_id>', methods=['POST'])
@login_required
def judge_score(team_id, event_id):

    if current_user.role not in ['mentor', 'admin']:
        abort(403)

    score_obj = Score.query.filter_by(
        team_id=team_id,
        hackathon_id=event_id
    ).first()

    if not score_obj:
        score_obj = Score(
            team_id=team_id,
            hackathon_id=event_id,
            mentor_id=current_user.id
        )

    score_obj.score = request.form['score']

    db.session.add(score_obj)
    db.session.commit()

    flash("Score submitted successfully!", "success")
    return redirect(url_for('routes.hackathons_view'))


# ---------------------------------------------------------
# LEADERBOARD PAGE
# ---------------------------------------------------------
@routes.route('/hackathon/<int:event_id>/leaderboard')
@login_required
def hackathon_leaderboard(event_id):
    results = (
        db.session.query(Team, db.func.avg(Score.score).label("avg_score"))
        .join(Score, Score.team_id == Team.id)
        .filter(Team.hackathon_id == event_id)
        .group_by(Team.id)
        .order_by(db.desc("avg_score"))
        .all()
    )

    hackathon = Hackathon.query.get_or_404(event_id)

    return render_template(
        'hackathon_leaderboard.html',
        hackathon=hackathon,
        rankings=results
    )

# ---------------- TEAMS ----------------
@routes.route('/teams', methods=['GET','POST'])
@login_required
def teams_view():
    if request.method=='POST':
        team_name = request.form.get('team_name','').strip()
        idea_name = request.form.get('idea_name','').strip()
        section = request.form.get('section','').strip()
        year = request.form.get('year','').strip()
        department = request.form.get('department','').strip()

        if not team_name:
            flash("Team name required.", "danger")
            return redirect(url_for('routes.teams_view'))

        new_team = Team(
            name=team_name,
            leader_id=current_user.id,
            idea_name=idea_name or None,
            section=section or None,
            year=year or None,
            department=department or None,
            status='Active',
            created_at=datetime.utcnow()
        )
        db.session.add(new_team)
        db.session.commit()

        member_names = request.form.getlist('member_name[]')
        member_sections = request.form.getlist('member_section[]')
        member_years = request.form.getlist('member_year[]')
        member_departments = request.form.getlist('member_department[]')

        for i in range(len(member_names)):
            if member_names[i].strip()=='':
                continue
            member = TeamMember(
                team_id=new_team.id,
                name=member_names[i].strip(),
                section=member_sections[i] if i < len(member_sections) else None,
                year=member_years[i] if i < len(member_years) else None,
                department=member_departments[i] if i < len(member_departments) else None,
                user_id=None
            )
            db.session.add(member)
        db.session.commit()
        flash("Team created successfully!", "success")
        return redirect(url_for('routes.teams_view'))

    user_teams = Team.query.outerjoin(TeamMember).filter(
        or_(Team.leader_id == current_user.id, TeamMember.user_id == current_user.id)
    ).all()
    return render_template('teams.html', user_teams=user_teams)

@routes.route('/team/<int:team_id>')
@login_required
def team_detail_view(team_id):
    team = Team.query.get_or_404(team_id)
    return render_template('team_detail.html', team=team)

@routes.route('/team/delete/<int:team_id>', methods=['POST'])
@login_required
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    if team.leader_id != current_user.id:
        flash("Unauthorized action!", "danger")
        return redirect(url_for('routes.teams_view'))
    db.session.delete(team)
    db.session.commit()
    flash("Team deleted successfully.", "info")
    return redirect(url_for('routes.teams_view'))

@routes.route('/team/edit/<int:team_id>', methods=['GET','POST'])
@login_required
def edit_team_view(team_id):
    team = Team.query.get_or_404(team_id)
    if team.leader_id != current_user.id:
        flash("Unauthorized action!", "danger")
        return redirect(url_for('routes.teams_view'))

    if request.method=='POST':
        team.name = request.form.get('team_name', team.name)
        team.idea_name = request.form.get('idea_name', team.idea_name)
        team.section = request.form.get('section', team.section)
        team.year = request.form.get('year', team.year)
        team.department = request.form.get('department', team.department)
        db.session.commit()
        flash("Team updated successfully!", "success")
        return redirect(url_for('routes.team_detail_view', team_id=team.id))

    return render_template('edit_team.html', team=team)

# Upload Document
# ---------------- Document routes (secure + robust) ----------------
@routes.route('/upload', methods=['POST'])
@login_required
def upload_document():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.root_path, 'static', 'uploads', filename))

        # Save to database immediately
        doc = Document(
            filename=filename,
            user_id=current_user.id,  # assign the uploading user
            upload_date=datetime.utcnow()
        )
        db.session.add(doc)
        db.session.commit()
        flash('File uploaded successfully!')

    return redirect(url_for('some_page'))

@routes.route('/view_document/<filename>')
@login_required
def view_document(filename):
    uploads_folder = os.path.join(current_app.root_path, "static", "uploads")

    safe_name = os.path.basename(filename)
    file_path = os.path.join(uploads_folder, safe_name)

    if not os.path.exists(file_path):
        abort(404)

    return send_file(file_path)




@routes.route('/delete_document/<filename>', methods=['POST'])
@login_required
def delete_document(filename):
    document = Document.query.filter_by(filename=filename).first_or_404()

    # ownership check
    if getattr(document, 'user_id', None) != current_user.id and not getattr(current_user, 'is_admin', False):
        flash("Unauthorized action!", "danger")
        return redirect(request.referrer or url_for('routes.view_documents'))

    abs_folder = upload_folder_abs()
    file_path = os.path.join(abs_folder, document.filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        # ignore file deletion errors but continue to remove DB record
        pass

    db.session.delete(document)
    db.session.commit()
    flash('Document deleted successfully!', 'success')
    return redirect(request.referrer or url_for('routes.view_documents'))


@routes.route('/edit_document/<filename>', methods=['GET', 'POST'])
@login_required
def edit_document(filename):
    document = Document.query.filter_by(filename=filename).first_or_404()

    # ownership check
    if getattr(document, 'user_id', None) != current_user.id and not getattr(current_user, 'is_admin', False):
        flash("Unauthorized action!", "danger")
        return redirect(request.referrer or url_for('routes.view_documents'))

    if request.method == 'POST':
        new_name = request.form.get('new_name', '').strip()
        if not new_name:
            flash('New name cannot be empty!', 'danger')
            return redirect(url_for('routes.edit_document', filename=document.filename))

        # secure and preserve extension if user forgot it
        new_filename = secure_filename(new_name)
        # if user provided name without extension, append old extension
        if '.' not in new_filename:
            old_ext = os.path.splitext(document.filename)[1]
            new_filename = f"{new_filename}{old_ext}"

        if not allowed_file(new_filename):
            flash('Invalid file extension for new name!', 'danger')
            return redirect(url_for('routes.edit_document', filename=document.filename))

        abs_folder = upload_folder_abs()
        old_path = os.path.join(abs_folder, document.filename)
        new_path = os.path.join(abs_folder, new_filename)

        # avoid overwriting existing files: if exists, add timestamp suffix
        if os.path.exists(new_path):
            base, ext = os.path.splitext(new_filename)
            new_filename = f"{base}_{int(datetime.utcnow().timestamp())}{ext}"
            new_path = os.path.join(abs_folder, new_filename)

        try:
            os.rename(old_path, new_path)
        except FileNotFoundError:
            # old file missing — still update DB filename so user doesn't get broken link
            pass
        except Exception as e:
            flash(f'Error renaming file: {e}', 'danger')
            return redirect(url_for('routes.edit_document', filename=document.filename))

        document.filename = new_filename
        db.session.commit()
        flash('Document renamed successfully!', 'success')
        return redirect(url_for('routes.view_documents'))

    return render_template('edit_document.html', document=document)


@routes.route('/documents')
@login_required
def view_documents():
    # Admin: see all documents
    if getattr(current_user, 'role', '') == 'admin':
        documents = Document.query.order_by(Document.upload_date.desc()).all()
    else:
        # Normal users: only see their own docs
        documents = Document.query.filter_by(
            user_id=current_user.id
        ).order_by(Document.upload_date.desc()).all()

    # Pass to template
    return render_template('documents.html', documents=documents)

# ---------------- CHAT: chat_with_mentor ----------------
@routes.route('/chat/mentor/<int:mentor_id>', methods=['GET', 'POST'])
@login_required
def chat_with_mentor(mentor_id):
    mentor = User.query.get_or_404(mentor_id)

    if request.method == 'POST':
        text = request.form.get('message')

        if text:
            msg = ChatMessage(
                sender_id=current_user.id,
                receiver_id=mentor.id,
                message=text
            )
            db.session.add(msg)
            db.session.commit()

    messages = ChatMessage.query.filter(
        ((ChatMessage.sender_id == current_user.id) & (ChatMessage.receiver_id == mentor.id)) |
        ((ChatMessage.sender_id == mentor.id) & (ChatMessage.receiver_id == current_user.id))
    ).order_by(ChatMessage.timestamp).all()

    return render_template(
        'chat.html',
        mentor=mentor,
        messages=messages
    )







# ---------------- DEBUG ----------------
@routes.route('/_show_routes')
def _show_routes():
    rules = sorted([(r.endpoint, r.rule) for r in current_app.url_map.iter_rules()], key=lambda x: x[0])
    return "<br>".join([f"{e} -> {u}" for e,u in rules])









