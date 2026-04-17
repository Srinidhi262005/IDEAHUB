from flask import Blueprint, render_template
from flask_login import login_required
from Ideahub.models import User, Department

mentors_bp = Blueprint('mentors', __name__)

@mentors_bp.route('/mentors')
@login_required
def mentors_view():
    faculty = (
        User.query
        .filter_by(role="faculty")
        .join(Department)
        .order_by(Department.name, User.name)
        .all()
    )

    dept_mentors = {}

    for f in faculty:
        if f.department:
            dept_name = f.department.name
            dept_mentors.setdefault(dept_name, []).append(f)

    return render_template(
        "mentors.html",
        dept_mentors=dept_mentors
    )







