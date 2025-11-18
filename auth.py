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
            # Redirect to login page with GET method
            return redirect(url_for('login'), code=302)
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

def check_permission(endpoint, permission_type='read'):
    """
    Check if current user has specific permission for an endpoint.
    
    Args:
        endpoint: The route endpoint (e.g., 'manage_members')
        permission_type: Type of permission ('create', 'read', 'update', 'delete', 'approve', 'export')
    
    Returns:
        Boolean indicating if user has permission
    """
    if 'role' not in session:
        return False
    
    # Super Admin has all permissions
    if session.get('role') == 'Super Admin':
        return True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        
        permission_column = f'can_{permission_type}'
        
        cursor.execute(f"""
            SELECT rr.{permission_column}
            FROM roles r
            JOIN role_routes rr ON r.role_id = rr.role_id
            JOIN routes rt ON rr.route_id = rt.route_id
            WHERE r.role_name = %s AND rt.endpoint = %s
        """, (session['role'], endpoint))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return bool(result[0]) if result else False
    except Exception as e:
        print(f"Error checking permission: {e}")
        return False

def permission_required(endpoint, permission_type='read'):
    """
    Decorator to require specific CRUD permission for a route.
    
    Usage: 
        @permission_required('manage_members', 'create')
        @permission_required('manage_members', 'update')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'payroll_number' not in session:
                flash('Please login to access this page', 'warning')
                return redirect(url_for('login'))
            
            if not check_permission(endpoint, permission_type):
                flash(f'Access denied. You do not have {permission_type} permission for this action.', 'danger')
                return redirect(url_for('navigation'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_user_permissions(endpoint):
    """
    Get all CRUD permissions for current user on a specific endpoint.
    
    Returns dictionary with permission flags:
    {
        'can_create': True/False,
        'can_read': True/False,
        'can_update': True/False,
        'can_delete': True/False,
        'can_approve': True/False,
        'can_export': True/False
    }
    """
    if 'role' not in session:
        return {
            'can_create': False,
            'can_read': False,
            'can_update': False,
            'can_delete': False,
            'can_approve': False,
            'can_export': False
        }
    
    # Super Admin has all permissions
    if session.get('role') == 'Super Admin':
        return {
            'can_create': True,
            'can_read': True,
            'can_update': True,
            'can_delete': True,
            'can_approve': True,
            'can_export': True
        }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        
        cursor.execute("""
            SELECT rr.can_create, rr.can_read, rr.can_update, rr.can_delete, rr.can_approve, rr.can_export
            FROM roles r
            JOIN role_routes rr ON r.role_id = rr.role_id
            JOIN routes rt ON rr.route_id = rt.route_id
            WHERE r.role_name = %s AND rt.endpoint = %s
        """, (session['role'], endpoint))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return {
                'can_create': bool(result[0]),
                'can_read': bool(result[1]),
                'can_update': bool(result[2]),
                'can_delete': bool(result[3]),
                'can_approve': bool(result[4]),
                'can_export': bool(result[5])
            }
        else:
            return {
                'can_create': False,
                'can_read': False,
                'can_update': False,
                'can_delete': False,
                'can_approve': False,
                'can_export': False
            }
    except Exception as e:
        print(f"Error getting user permissions: {e}")
        return {
            'can_create': False,
            'can_read': False,
            'can_update': False,
            'can_delete': False,
            'can_approve': False,
            'can_export': False
        }

