# IDEAHUB

IDEAHUB is a Flask-based idea collaboration platform designed to help students, mentors, and faculty connect through projects, events, notifications, documents, and teams.

## Key Features

- User authentication and role-based access
- Mentor directory with searchable mentor profiles
- Project idea submission and collaboration requests
- Event publishing and filtering
- File upload and document management
- Real-time notifications and chat support

## Project Structure

- `Ideahub/` — main Flask application package
- `Ideahub/templates/` — Jinja2 HTML templates
- `Ideahub/static/` — application static assets
- `Ideahub/mentors/` — mentor-specific blueprint and routes
- `scripts/` — utility scripts for data import and seeding
- `instance/` — local runtime database and configuration storage
- `requirements.txt` — Python dependencies

## Development Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:

   ```bash
   python run.py
   ```

4. Open the app in your browser:

   ```text
   http://127.0.0.1:5001
   ```

## Optional Environment Variables

- `PORT` — HTTP port to run the app on
- `FLASK_DEBUG` — enable debug mode when set to `1`, `true`, or `True`
- `FLASK_SECRET_KEY` — override the default secret key
- `DATABASE_URL` — optional alternate SQLAlchemy database URI

## Database and Migrations

The app uses SQLite by default and stores the database in `instance/ideahub.db`.

Use the Flask CLI for migrations:

```bash
python manage.py db init
python manage.py db migrate
python manage.py db upgrade
```

## Notes

- Keep sensitive configuration out of Git.
- Avoid committing local files such as `venv/`, `instance/`, and `flask_session/`.
- If you use Windows, be sure to activate the virtual environment before installing dependencies.
