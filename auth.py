"""
Authentication and authorization functions
"""
from functools import wraps
from flask import session, redirect, url_for, flash
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db_connection

def login_required(f):
    """
    Decorator to require login for a route.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'payroll_number' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """
    Decorator to require specific role(s) for a route.
    Usage: @role_required('Super Admin', 'Finance')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'payroll_number' not in session:
                flash('Please login to access this page', 'warning')
                return redirect(url_for('login'))
            
            if 'role' not in session:
                flash('No role assigned to your account', 'danger')
                return redirect(url_for('navigation'))
            
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash(f'Access denied. Required roles: {", ".join(allowed_roles)}', 'danger')
                return redirect(url_for('navigation'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_authorized_routes():
    """
    Get list of routes the current user is authorized to access.
    Returns list of route dictionaries with route_name and endpoint.
    """
    if 'role' not in session:
        return []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        
        cursor.execute("""
            SELECT DISTINCT rt.route_name, rt.endpoint
            FROM roles r
            JOIN role_routes rr ON r.role_id = rr.role_id
            JOIN routes rt ON rr.route_id = rt.route_id
            WHERE r.role_name = %s
            ORDER BY rt.route_name
        """, (session['role'],))
        
        routes = []
        for row in cursor.fetchall():
            routes.append({
                'route_name': row[0],
                'endpoint': row[1]
            })
        
        cursor.close()
        conn.close()
        return routes
    except Exception as e:
        print(f"Error getting authorized routes: {e}")
        return []

def verify_password(stored_hash, password):
    """
    Verify password against stored hash.
    """
    try:
        return check_password_hash(stored_hash, password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def hash_password(password):
    """
    Generate password hash.
    """
    return generate_password_hash(password)

