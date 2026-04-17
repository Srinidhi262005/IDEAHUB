from functools import wraps
from flask_login import current_user
from flask import abort

def role_required(*roles):
    """
    Usage:
    @login_required
    @role_required('admin', 'mentor')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # Not logged in
            if current_user.role not in roles:
                abort(403)  # Forbidden
            return fn(*args, **kwargs)
        return wrapper
    return decorator
