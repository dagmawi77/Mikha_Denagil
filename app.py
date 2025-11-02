import math
from flask import Flask, Response, render_template, request, redirect, url_for, session, flash, send_file, make_response
import os
import time

# MySQL connector - much simpler than Oracle, no timezone issues!
import mysql.connector
from mysql.connector import Error as MySQLError
import tempfile
from flask import request, redirect, url_for
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import csv
import io
from io import StringIO
from fpdf import FPDF
from reportlab.lib.pagesizes import letter
from reportlab.lib.pagesizes import A3, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepInFrame
)
from openpyxl import Workbook  # To handle Excel export
import pandas as pd
from io import BytesIO
from math import ceil
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from datetime import datetime, timezone
from datetime import datetime, timedelta
import uuid
import io
import csv
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import make_response, flash, redirect, url_for
from threading import Thread
from collections import defaultdict
from datetime import date, timedelta

# Import translations module for bilingual support
from translations import get_text

app = Flask(__name__)


#app.run(host='0.0.0.0',port=5001,debug=True)
app.secret_key = 'your_secret_key'  # Change this to a secure key
app.permanent_session_lifetime = timedelta(minutes=3)  # Set session timeout to 3 minutes

def test_db_connection():
    """
    Test if MySQL database is reachable.
    Returns (success: bool, message: str)
    """
    try:
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='',
            database='aawsa_db',
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return True, "MySQL database connection successful"
    except MySQLError as e:
        return False, f"MySQL error {e.errno}: {e.msg}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

def get_db_connection():
    """
    Create connection to local MySQL database.
    Much simpler than Oracle - no timezone or listener issues!
    """
    try:
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='',
            database='aawsa_db',
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            autocommit=False
        )
        return conn
    except MySQLError as e:
        if e.errno == 2003:
            # Can't connect to MySQL server
            raise Exception(f"MySQL server is not running on localhost:3306. Please start MySQL service.")
        elif e.errno == 1045:
            # Access denied
            raise Exception(f"MySQL access denied. Check username/password: root/(empty)")
        elif e.errno == 1049:
            # Unknown database
            raise Exception(f"MySQL database 'aawsa_db' does not exist. Please run the setup script first.")
        else:
            raise Exception(f"MySQL connection error {e.errno}: {e.msg}")
    except Exception as e:
        raise Exception(f"Unable to connect to MySQL database: {str(e)}")

def get_db_connection_billing():
    """
    Create connection to billing MySQL database on remote server.
    """
    try:
        conn_bill = mysql.connector.connect(
            host='10.12.110.14',
            port=3306,
            user='billing_user',
            password='billing_password',
            database='billing_db',
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            autocommit=False
        )
        return conn_bill
    except MySQLError as e:
        if e.errno == 2003:
            raise Exception(f"Billing MySQL server is not reachable at 10.12.110.14:3306")
        elif e.errno == 1045:
            raise Exception(f"Billing database access denied. Check credentials.")
        else:
            raise Exception(f"Billing MySQL error {e.errno}: {e.msg}")
    except Exception as e:
        raise Exception(f"Unable to connect to billing database: {str(e)}")
# Middleware to track session timeout
def track_session_timeout():
    if 'last_activity' in session:
        now = datetime.now()
        last_activity = session['last_activity']
        if (now - last_activity).total_seconds() > 180:  # 3 minutes
            session.clear()  # Clear session if inactive for more than 3 minutes
            flash("Session timed out due to inactivity.", "warning")
            return redirect(url_for('login'))
    session['last_activity'] = datetime.now()  # Update last activity time

@app.before_request
def make_session_permanent():
    session.permanent = True 

# Decorator to protect routes
def session_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'payroll_number' not in session:  # Check if user is logged in
            flash("Please log in to access this page.", "danger")
            return redirect(url_for('login'))
        track_session_timeout()  # Track session timeout on each request
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'payroll_number' not in session:
                flash('Please log in to access this page', 'danger')
                return redirect(url_for('login'))

            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                # Get user's role
                cursor.execute("""
                    SELECT r.role_name 
                    FROM aawsa_user u
                    JOIN roles r ON u.role_id = r.role_id
                    WHERE u.payroll_number = %(payroll_number)s
                """, {'payroll_number': session['payroll_number']})
                user_role = cursor.fetchone()
                
                if not user_role or user_role[0] not in allowed_roles:
                    flash('You do not have permission to access this page', 'danger')
                    return redirect(url_for('navigation'))
                
                return f(*args, **kwargs)
            finally:
                cursor.close()
                conn.close()
        return decorated_function
    return decorator

# Example usage:
@app.route('/admin_dashboard')
@role_required('Super Admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.context_processor
def inject_navigation():
    def get_authorized_routes():
        if 'payroll_number' not in session:
            return []
            
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT r.endpoint, r.route_name
                FROM routes r
                JOIN role_routes rr ON r.route_id = rr.route_id
                JOIN roles ro ON rr.role_id = ro.role_id
                JOIN aawsa_user u ON ro.role_id = u.role_id
                WHERE u.payroll_number = %(payroll_number)s
                ORDER BY r.route_name
            """, {'payroll_number': session['payroll_number']})
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    
    return dict(authorized_routes=get_authorized_routes())

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        payroll_number = request.form['payroll_number']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user with hashed password
        cursor.execute("""
            SELECT u.*, r.role_name 
            FROM aawsa_user u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.payroll_number = %(payroll_number)s
        """, {"payroll_number": payroll_number})
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[4], password):  # user[4] is password_hash
            session['payroll_number'] = payroll_number
            session['role'] = user[-1]  # Or: user['role_name']
            session['last_activity'] = datetime.now().isoformat()
            flash("Login successful!", "success")
            return redirect(url_for('navigation'))
        else:
            flash("Invalid credentials", "danger")

    return render_template('login.html')




app.secret_key = 'your_very_strong_secret_key_here'  # Change this to a secure random key
app.permanent_session_lifetime = timedelta(minutes=30)  # Session expires after 30 minutes

@app.before_request
def check_session():
    # Skip session check for login page and static files
    if request.endpoint in ['login', 'static']:
        return
    
    # Check if user is logged in
    if 'payroll_number' not in session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('login'))
    
    # Check session timeout
    last_activity = session.get('last_activity')
    if last_activity:
        # Convert ISO string back to datetime object
        last_activity_dt = datetime.fromisoformat(last_activity)
        if (datetime.now() - last_activity_dt).total_seconds() > 1800:
            session.clear()
            flash('Session timed out due to inactivity', 'warning')
            return redirect(url_for('login'))
    
    # Update last activity time
    session['last_activity'] = datetime.now().isoformat()


# Middleware to protect routes (login required)
def login_required(func):
    def wrapper(*args, **kwargs):
        if 'payroll_number' not in session:
            # Redirect to the login page if not logged in
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__  # Ensure the function name is correct for routing
    return wrapper

def initialize_rbac_tables():
    """
    Initialize RBAC tables if they don't exist.
    This function is called at startup but won't crash the app if DB is down.
    """
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"⚠ WARNING: Cannot initialize RBAC tables - {str(e)}")
        print("⚠ The application will start but database features won't work until the database is available.")
        return False
    
    cursor = conn.cursor(buffered=True)
    
    try:
        # Create RBAC tables in MySQL - much simpler than Oracle!
        
        # Create roles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                role_id INT AUTO_INCREMENT PRIMARY KEY,
                role_name VARCHAR(100) NOT NULL UNIQUE,
                description VARCHAR(255)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create routes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS routes (
                route_id INT AUTO_INCREMENT PRIMARY KEY,
                route_name VARCHAR(100) NOT NULL UNIQUE,
                endpoint VARCHAR(255) NOT NULL UNIQUE,
                description VARCHAR(255)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create role_routes junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_routes (
                role_id INT NOT NULL,
                route_id INT NOT NULL,
                PRIMARY KEY (role_id, route_id),
                FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE,
                FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Check if aawsa_user table exists and add role_id column if needed
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'aawsa_db' 
            AND TABLE_NAME = 'aawsa_user' 
            AND COLUMN_NAME = 'role_id'
        """)
        result = cursor.fetchone()
        if result and result[0] == 0:
            # Add role_id column to existing aawsa_user table
            cursor.execute("""
                ALTER TABLE aawsa_user 
                ADD COLUMN role_id INT,
                ADD CONSTRAINT fk_user_role 
                FOREIGN KEY (role_id) REFERENCES roles(role_id)
            """)
        conn.commit()
        print("✓ RBAC tables initialized/verified successfully")
        return True
    except Exception as e:
        conn.rollback()
        print(f"✗ Error initializing RBAC tables: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

# Test database connection and initialize RBAC tables at application startup
print("\n" + "="*60)
print("Starting Application - Database Check")
print("="*60)

# Test connection first
db_ok, db_msg = test_db_connection()
if db_ok:
    print(f"✓ {db_msg}")
    # Initialize RBAC tables
    if initialize_rbac_tables():
        print("✓ Database initialization completed")
    else:
        print("⚠ Database initialization failed but app will continue")
else:
    print(f"✗ {db_msg}")
    print("⚠ WARNING: Database is not available!")
    print("⚠ Application will start but you need to:")
    print("   1. Start your MySQL database (localhost:3306)")
    print("   2. If you see ORA-01804 error, check FIX_ORA-01804_ERROR.md")
    print("   3. Restart the application after database is up")

print("="*60 + "\n")
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'payroll_number' not in session:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
@app.context_processor
def inject_navigation():
    def get_authorized_routes():
        if 'payroll_number' not in session:
            return []
            
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # First check if RBAC tables exist
            cursor.execute("""
            SELECT COUNT(*) FROM user_tables WHERE table_name = 'ROLES'
            """)
            if cursor.fetchone()[0] == 0:
                return []
                
            # Get user's authorized routes
            cursor.execute("""
                SELECT r.endpoint, r.route_name
                FROM routes r
                JOIN role_routes rr ON r.route_id = rr.route_id
                JOIN roles ro ON rr.role_id = ro.role_id
                JOIN aawsa_user u ON ro.role_id = u.role_id
                WHERE u.payroll_number = %(payroll_number)s
                ORDER BY r.route_name
            """, {'payroll_number': session['payroll_number']})
            return cursor.fetchall()
        except MySQLError as e:
            print(f"Error getting authorized routes: {str(e)}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    return dict(authorized_routes=get_authorized_routes())

@app.context_processor
def utility_processor():
    def get_assigned_routes(role_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.route_name 
            FROM routes r
            JOIN role_routes rr ON r.route_id = rr.route_id
            WHERE rr.role_id = %(role_id)s
        """, {'role_id': role_id})
        routes = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return routes
    return dict(get_assigned_routes=get_assigned_routes)

@app.context_processor
def inject_translation():
    """Inject translation function into all templates"""
    def t(key):
        lang = session.get('language', 'am')  # Default to Amharic
        return get_text(key, lang)
    return dict(t=t)

@app.route('/set_language/<lang>')
def set_language(lang):
    """Set the language preference in session"""
    if lang in ['am', 'en']:
        session['language'] = lang
        session.permanent = True
    # Redirect back to the previous page or to navigation
    return redirect(request.referrer or url_for('navigation'))

@app.route('/manage_roles')
@login_required
# @login_required
@role_required('Super Admin')  # Only Super Admin can access
def manage_roles():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all roles
    cursor.execute("SELECT role_id, role_name, description FROM roles ORDER BY role_name")
    roles = cursor.fetchall()
    
    # Get all routes for the role assignment form
    cursor.execute("SELECT route_id, route_name FROM routes ORDER BY route_name")
    all_routes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('manage_roles.html', 
                         roles=roles,
                         all_routes=all_routes)

@app.route('/add_role', methods=['POST'])
@login_required
# @login_required
@role_required('Super Admin') 
# @login_required
# @role_required('Super Admin')
def add_role():
    role_name = request.form['role_name']
    description = request.form.get('description', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO roles (role_name, description)
            VALUES (%(role_name)s, %(description)s)
        """, {'role_name': role_name, 'description': description})
        conn.commit()
        flash('Role created successfully!', 'success')
    except MySQLError as e:
        conn.rollback()
        flash(f'Error creating role: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('manage_roles'))

@app.route('/update_role_routes/<int:role_id>', methods=['POST'])
@login_required
# @login_required
@role_required('Super Admin') 
# @login_required
# @role_required('Super Admin')
def update_role_routes(role_id):
    selected_routes = request.form.getlist('routes')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Clear existing routes for this role
        cursor.execute("DELETE FROM role_routes WHERE role_id = %(role_id)s", 
                      {'role_id': role_id})
        
        # Add the new selected routes
        for route_id in selected_routes:
            cursor.execute("""
                INSERT INTO role_routes (role_id, route_id)
                VALUES (%(role_id)s, %(route_id)s)
            """, {'role_id': role_id, 'route_id': route_id})
        
        conn.commit()
        flash('Route permissions updated successfully!', 'success')
    except MySQLError as e:
        conn.rollback()
        flash(f'Error updating route permissions: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('manage_roles'))

@app.route('/delete_role/<int:role_id>', methods=['POST'])
@login_required
# @login_required
@role_required('Super Admin') 
# @login_required
# @role_required('Super Admin')
def delete_role(role_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # First check if any users have this role
        cursor.execute("SELECT COUNT(*) FROM aawsa_user WHERE role_id = %(role_id)s", 
                      {'role_id': role_id})
        user_count = cursor.fetchone()[0]
        
        if user_count > 0:
            flash('Cannot delete role - there are users assigned to it!', 'danger')
        else:
            # Delete role routes first
            cursor.execute("DELETE FROM role_routes WHERE role_id = %(role_id)s", 
                          {'role_id': role_id})
            # Then delete the role
            cursor.execute("DELETE FROM roles WHERE role_id = %(role_id)s", 
                          {'role_id': role_id})
            conn.commit()
            flash('Role deleted successfully!', 'success')
    except MySQLError as e:
        conn.rollback()
        flash(f'Error deleting role: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('manage_roles'))

def initialize_default_roles_and_routes():
    """
    Initialize default roles and routes if they don't exist.
    This function is called at startup but won't crash the app if DB is down.
    """
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"⚠ WARNING: Cannot initialize default roles and routes - {str(e)}")
        print("⚠ The application will start but RBAC features won't work until the database is available.")
        return False
    
    cursor = conn.cursor()
    
    try:
        # Create default roles
        default_roles = [
            ('Super Admin', 'Full access to all system features'),
            ('Finance', 'Access to billing, payments, and financial reports'),
            ('Customer Service', 'Access to customer data and support functions'),
            ('Branch Manager', 'Access to branch-specific operations')
        ]
        
        for role_name, description in default_roles:
            cursor.execute("""
                INSERT IGNORE INTO roles (role_name, description)
                VALUES (%(role_name)s, %(description)s)
            """, {'role_name': role_name, 'description': description})
        
        # Create default routes
        default_routes = [
            ('Dashboard', 'navigation', 'Main dashboard'),
            ('List Paid Bills', 'list_paid_bills', 'View paid bills'),
            ('List Sent Bills', 'list_sent_bills', 'View sent bills'),
            ('List Unsettled Bills', 'list_unsettled_bills', 'View unsettled bills'),
            ('Call Center Unsettled', 'call_center_unsettled', 'Call center unresolved issues'),
            ('Reports', 'report_page', 'View reports'),
            ('Export Data', 'export_form', 'Export data'),
            ('User Management', 'create_user', 'Manage users'),
            ('Role Management', 'manage_roles', 'Manage roles'),
            ('Route Management', 'manage_routes', 'Manage routes'),
            ('Upload Bills', 'upload_bill', 'Upload bill data'),
            ('Upload VAT', 'upload_vat', 'Upload VAT data'),
            ('Move Data', 'move_data', 'Archive old data')
        ]
        
        for route_name, endpoint, description in default_routes:
            cursor.execute("""
                INSERT IGNORE INTO routes (route_name, endpoint, description)
                VALUES (%(route_name)s, %(endpoint)s, %(description)s)
            """, {
                'route_name': route_name,
                'endpoint': endpoint,
                'description': description
            })
        
        # Assign all routes to Super Admin
        cursor.execute("SELECT role_id FROM roles WHERE role_name = 'Super Admin'")
        super_admin_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT route_id FROM routes")
        all_route_ids = [row[0] for row in cursor.fetchall()]
        
        for route_id in all_route_ids:
            cursor.execute("""
                INSERT IGNORE INTO role_routes (role_id, route_id)
                VALUES (%(role_id)s, %(route_id)s)
            """, {'role_id': super_admin_id, 'route_id': route_id})
        
        conn.commit()
        print("✓ Default roles and routes initialized successfully")
        return True
    except Exception as e:
        conn.rollback()
        print(f"✗ Error initializing default roles and routes: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

# Initialize default roles and routes at startup (won't crash if DB is down)
print("Initializing default roles and routes...")
if initialize_default_roles_and_routes():
    print("✓ Default roles and routes setup completed")
else:
    print("⚠ Default roles and routes setup failed but app will continue")
print()

@app.route('/roles/<int:role_id>/routes', methods=['GET', 'POST'])
@login_required
# @login_required
@role_required('Super Admin') 
def manage_role_routes(role_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Update the routes assigned to this role
        selected_routes = request.form.getlist('routes')
        
        try:
            # First clear existing routes for this role
            cursor.execute("DELETE FROM role_routes WHERE role_id = %(role_id)s", {'role_id': role_id})
            
            # Add the new selected routes
            for route_id in selected_routes:
                cursor.execute("""
                    INSERT INTO role_routes (role_id, route_id)
                    VALUES (%(role_id)s, %(route_id)s)
                """, {'role_id': role_id, 'route_id': route_id})
            
            conn.commit()
            flash('Route permissions updated successfully!', 'success')
        except MySQLError as e:
            conn.rollback()
            flash(f'Error updating route permissions: {str(e)}', 'danger')
        
        return redirect(url_for('manage_role_routes', role_id=role_id))
    
    # GET request - show current routes and available routes
    # Get role info
    cursor.execute("SELECT role_name FROM roles WHERE role_id = %(role_id)s", {'role_id': role_id})
    role = cursor.fetchone()
    
    if not role:
        flash('Role not found', 'danger')
        return redirect(url_for('manage_roles'))
    
    # Get all available routes
    cursor.execute("SELECT route_id, route_name, endpoint FROM routes ORDER BY route_name")
    all_routes = cursor.fetchall()
    
    # Get routes currently assigned to this role
    cursor.execute("""
        SELECT r.route_id, r.route_name 
        FROM routes r
        JOIN role_routes rr ON r.route_id = rr.route_id
        WHERE rr.role_id = %(role_id)s
    """, {'role_id': role_id})
    assigned_routes = {row[0] for row in cursor.fetchall()}
    
    cursor.close()
    conn.close()
    
    return render_template('manage_role_routes.html', 
                         role={'role_id': role_id, 'role_name': role[0]},
                         all_routes=all_routes,
                         assigned_routes=assigned_routes)

@app.route('/routes', methods=['GET', 'POST'])
@login_required
# @login_required
@role_required('Super Admin') 
# @login_required
def manage_routes():
    if request.method == 'POST':
        route_name = request.form['route_name']
        endpoint = request.form['endpoint']
        description = request.form.get('description', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO routes (route_name, endpoint, description)
                VALUES (%(route_name)s, %(endpoint)s, %(description)s)
            """, {
                'route_name': route_name,
                'endpoint': endpoint,
                'description': description
            })
            conn.commit()
            flash('Route added successfully!', 'success')
        except MySQLError as e:
            conn.rollback()
            flash(f'Error adding route: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('manage_routes'))
    
    # GET request - show all routes
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT route_id, route_name, endpoint, description FROM routes")
    routes = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('manage_routes.html', routes=routes)


# Middleware to protect routes (login required)
def login_required(func):
    def wrapper(*args, **kwargs):
        if 'payroll_number' not in session:
            # Redirect to the login page if not logged in
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__  # Ensure the function name is correct for routing
    return wrapper



@app.route('/navigation')
@login_required
def navigation():
    connection = get_db_connection()
    
    # Initialize all variables with default values
    recent_sent_bills = []
    total_bills = [0, 'N/A', 0, 0]  # Default values for count, reason, total, current month
    payment_total = [0, 'N/A', 0, 0]
    comparison = [0, 0, 0, 0]  # paid, sent, number_sent, number_paid
    branch_stats = []
    payment_by_channel = []
    current_settled = []
    current_delivery = []
    current_unsettled = []
    
    try:
        cursor = connection.cursor(buffered=True)
        
        # Get summary report data by section
        cursor.execute("""
            SELECT 
                m.section_name,
                SUM(CASE WHEN m.gender IN ('ወንድ', 'Male') THEN 1 ELSE 0 END) as male_count,
                SUM(CASE WHEN m.gender IN ('ሴት', 'Female') THEN 1 ELSE 0 END) as female_count,
                SUM(CASE WHEN m.marital_status IN ('ያላገባ', 'ያላገባች', 'Single') THEN 1 ELSE 0 END) as single_count,
                SUM(CASE WHEN m.marital_status IN ('ያገባ', 'Married') THEN 1 ELSE 0 END) as married_count,
                SUM(CASE WHEN m.work_status IN ('በሥራ ላይ', 'Employed') THEN 1 ELSE 0 END) as employed_count,
                SUM(CASE WHEN m.work_status IN ('ስራ የለኝም', 'Unemployed') THEN 1 ELSE 0 END) as unemployed_count,
                SUM(CASE WHEN m.work_status IN ('ስራ በመፈለግ ላይ') THEN 1 ELSE 0 END) as seeking_count,
                SUM(CASE WHEN m.work_status IN ('ተማሪ', 'Student') OR m.student IN ('Yes', 'አዎ') THEN 1 ELSE 0 END) as student_count
            FROM member_registration m
            GROUP BY m.section_name
            ORDER BY m.section_name
        """)
        current_settled = cursor.fetchall()
        
        # Get total members for card
        cursor.execute("SELECT COUNT(*) FROM member_registration")
        total_members = cursor.fetchone()[0] or 0
        total_bills = [total_members, datetime.now().strftime('%B %Y'), 0, 0]
        
        # Get section counts for other cards
        cursor.execute("""
            SELECT section_name, COUNT(*) 
            FROM member_registration 
            GROUP BY section_name
        """)
        section_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        children_count = section_counts.get('የሕፃናት ክፍል', 0)
        youth_count = section_counts.get('ወጣት ክፍል', 0)
        
        payment_total = [children_count, f'{children_count} አባላት', youth_count, f'{youth_count} አባላት']
        
    except Exception as e:
        app.logger.error(f"Error in navigation route: {str(e)}", exc_info=True)
        # Continue with default values if there's an error
        
    finally:
        connection.close()

    # Extract values with null checks
    total_paid_amount = comparison[0] if len(comparison) > 0 else 0
    total_sent_amount = comparison[1] if len(comparison) > 1 else 0
    number_sent = comparison[2] if len(comparison) > 2 else 0
    number_paid = comparison[3] if len(comparison) > 3 else 0

    
    current_bill_count = total_bills[0] if len(total_bills) > 0 else 0
    bill_period = total_bills[1] if len(total_bills) > 1 else 'N/A'
    current_month_total_bill_amnt = total_bills[2] if len(total_bills) > 2 else 0
    current_month_bill_amnt = total_bills[3] if len(total_bills) > 3 else 0
    
    payment_count = payment_total[0] if len(payment_total) > 0 else 0
    payment_month = payment_total[1] if len(payment_total) > 1 else 'N/A'
    payment_total_bill_amnt = payment_total[2] if len(payment_total) > 2 else 0
    payment_this_month_bill_amnt = payment_total[3] if len(payment_total) > 1 else 'N/A'

    # Prepare data for charts with null checks
    branch_labels = [row[0] for row in branch_stats] if branch_stats else []
    number_sent_data = [row[1] for row in branch_stats] if branch_stats else []
    total_amount_sent_data = [row[2] for row in branch_stats] if branch_stats else []
    outstanding_amount = [row[3] for row in branch_stats] if branch_stats else []
    this_month_bill_amnt = [row[4] for row in branch_stats] if branch_stats else []

    channel_labels = [row[0] for row in payment_by_channel] if payment_by_channel else []
    channel_amounts = [row[1] for row in payment_by_channel] if payment_by_channel else []

    return render_template(
        'navigation.html',
        recent_sent_bills=recent_sent_bills,
        current_settled=current_settled,
        current_delivery=current_delivery,
        current_unsettled=current_unsettled,
        total_paid_amount=total_paid_amount,
        total_sent_amount=total_sent_amount,
        total_bills=total_bills,
        number_sent=number_sent,
        current_bill_count=current_bill_count,
        bill_period=bill_period,
        current_month_total_bill_amnt=current_month_total_bill_amnt,
        current_month_bill_amnt=current_month_bill_amnt,
        payment_count=payment_count,
        payment_month=payment_month,
        payment_total_bill_amnt=payment_total_bill_amnt,
        payment_this_month_bill_amnt=payment_this_month_bill_amnt,
        branch_labels=branch_labels,
        number_sent_data=number_sent_data,
        total_amount_sent_data=total_amount_sent_data,
        outstanding_amount=outstanding_amount,
        this_month_bill_amnt=this_month_bill_amnt,
        channel_labels=channel_labels,
        channel_amounts=channel_amounts
    )
@app.route('/dashboard-data')
@login_required
def dashboard_data():
    connection = get_db_connection()
    
    data = {
        # Card metrics
        'current_bill_count': "0",
        'bill_period': 'N/A',
        'current_month_total_bill_amnt': "0",
        'current_month_bill_amnt': "0",
        'payment_count': "0",
        'payment_month': 'N/A',
        'payment_total_bill_amnt': "0",
        'payment_this_month_bill_amnt': 'N/A',

        
        # Branch status tables
        'current_settled': [],
        'current_delivery': [],
        'current_unsettled': [],
        
        # Charts data
        'branch_labels': [],
        'number_sent_data': [],
        'total_amount_sent_data': [],
        'outstanding_amount': [],
        'this_month_bill_amnt': [],
        'channel_labels': [],
        'channel_amounts': []
    }
    
    try:
        cursor = connection.cursor()
        
        # Get bill statistics
        cursor.execute(""" 
            SELECT count(*)

            FROM MEMBER_REGISTRATION 
        """)
        total_bills = cursor.fetchone()
        if total_bills:
            data.update({
                'current_bill_count': total_bills[0],
            })


        # Get payment statistics
        cursor.execute(""" 
            SELECT count(*),SECTION_NAME
            FROM MEMBER_REGISTRATION  where SECTION_NAME='የሕፃናት ክፍል'
                       group by  SECTION_NAME
        """)
        
        payment = cursor.fetchone()
        if payment:
            data.update({
                'payment_count': payment[0],
                'payment_month': payment[1] or 'N/A',
                # 'payment_total_bill_amnt': payment[2] or "0",
                # 'payment_this_month_bill_amnt': payment[3] or "0"
            })
            cursor.execute(""" 
            SELECT count(*),SECTION_NAME
            FROM MEMBER_REGISTRATION  where SECTION_NAME='ወጣት ክፍል'
                       group by  SECTION_NAME
        """)
        payment = cursor.fetchone()
        if payment:
            data.update({
                'payment_total_bill_amnt': payment[0],
                'payment_this_month_bill_amnt': payment[1] or 'N/A',
                # 'payment_total_bill_amnt': payment[2] or "0",
                # 'payment_this_month_bill_amnt': payment[3] or "0"
            })

        # Get branch-based data for charts
        cursor.execute("""
            
SELECT
    SECTION_NAME AS PAYMENTCHANNEL,
    COUNT(CASE WHEN GENDER = 'ወንድ' THEN 1 END) AS MALE_COUNT,
    COUNT(CASE WHEN GENDER = 'ሴት' THEN 1 END) AS FEMALE_COUNT
FROM 
    MEMBER_REGISTRATION
GROUP BY 
    SECTION_NAME
ORDER BY 
    SECTION_NAME
        """)
        branch_stats = cursor.fetchall()
        if branch_stats:
            data['branch_labels'] = [row[0] for row in branch_stats]
            data['number_sent_data'] = [row[1] for row in branch_stats]
            data['total_amount_sent_data'] = [row[2] for row in branch_stats]
            # data['outstanding_amount'] = [row[3] for row in branch_stats]
            # data['this_month_bill_amnt'] = [row[4] for row in branch_stats]

        # Get payment channels data
        cursor.execute("""
            SELECT SECTION_NAME as PAYMENTCHANNEL
    , count(*) AS total_amount
            FROM MEMBER_REGISTRATION p
            GROUP BY p.SECTION_NAME
        """)
        payment_by_channel = cursor.fetchall()
        if payment_by_channel:
            data['channel_labels'] = [row[0] for row in payment_by_channel]
            data['channel_amounts'] = [float(row[1]) for row in payment_by_channel]

        # Get settled bills
        cursor.execute("""
            SELECT
    SECTION_NAME AS PAYMENTCHANNEL,
    COUNT(CASE WHEN GENDER = 'ወንድ' THEN 1 END) AS MALE_COUNT,
    COUNT(CASE WHEN GENDER = 'ሴት' THEN 1 END) AS FEMALE_COUNT,
    COUNT(CASE WHEN MARITAL_STATUS = 'ያላገባ' THEN 1 END) AS meried_COUNT,
    COUNT(CASE WHEN MARITAL_STATUS = 'ያገባ' THEN 1 END) AS meried_COUNT,
    COUNT(CASE WHEN WORK_STATUS = 'በሥራ ላይ' THEN 1 END) AS on_work,
    COUNT(CASE WHEN WORK_STATUS = 'ስራ የለኝም' THEN 1 END) AS not_work,
    COUNT(CASE WHEN WORK_STATUS = 'ስራ በመፈለግ ላይ' THEN 1 END) AS finding_job,
    COUNT(CASE WHEN WORK_STATUS = 'ተማሪ' THEN 1 END) AS student
    
FROM 
    MEMBER_REGISTRATION
GROUP BY 
    SECTION_NAME
ORDER BY 
    SECTION_NAME
        """)
        data['current_settled'] = [list(row) for row in cursor.fetchall()] or []

        # Get delivery bills
        cursor.execute("""
            SELECT CUSTOMERBRANCH, REASON, 
                   TO_CHAR(COUNT(*),'FM999,999,999'),
                   TO_CHAR(SUM(CONS),'FM999,999,999'),
                   TO_CHAR(SUM(THISMONTHBILLAMT),'FM999,999,999'),
                   TO_CHAR(SUM(OUTSTANDINGAMT),'FM999,999,999'),
                   TO_CHAR(SUM(TOTALBILLAMOUNT),'FM999,999,999')
            FROM bill where REASON!='March-2025'
            GROUP BY CUSTOMERBRANCH, REASON
        """)
        data['current_delivery'] = [list(row) for row in cursor.fetchall()] or []

        # Get unsettled bills
        cursor.execute("""
            SELECT CUSTOMERBRANCH, REASON, 
                   TO_CHAR(COUNT(*),'FM999,999,999'),
                   TO_CHAR(SUM(CONS),'FM999,999,999'),
                   TO_CHAR(SUM(THISMONTHBILLAMT),'FM999,999,999'),
                   TO_CHAR(SUM(OUTSTANDINGAMT),'FM999,999,999'),
                   TO_CHAR(SUM(TOTALBILLAMOUNT),'FM999,999,999')
            FROM bill 
            WHERE billkey NOT IN (SELECT billkey FROM payment) and REASON!='March-2025'
            GROUP BY CUSTOMERBRANCH, REASON
        """)
        data['current_unsettled'] = [list(row) for row in cursor.fetchall()] or []
        
    except Exception as e:
        app.logger.error(f"Error in dashboard-data route: {str(e)}", exc_info=True)
        data['error'] = True
        data['message'] = str(e)
        
    finally:
        connection.close()

    return jsonify(data)
@app.route('/start_payment')
@login_required
# @login_required
@role_required('Super Admin') 
def start_payment():
    return render_template('start_payment.html')

@app.route('/end_payment')
@login_required
# @login_required
@role_required('Super Admin') 
def end_payment():
    return render_template('end_payment.html')




@app.route('/attendance_report', methods=['GET', 'POST'])
@login_required
def attendance_report():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 50  # Number of items per page
    start_date = request.args.get('start_date', '')  # Get start date for date filtering
    end_date = request.args.get('end_date', '')  # Get end date for date filtering

    if request.method == 'POST':
        search_query = request.form.get('search', '')
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')

    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
      select FULL_NAME,GENDER,CHRISTIAN_NAME,PHONE,SECTION_NAME,ATTENDANCE_DATE,PRESENT_STATUS from 
    MEMBER_REGISTRATION a, attendance b where a.id=b.member_id
    """

    params = {}

    # Add search filter if search_query is provided
    if search_query:
        query += " AND (a.FULL_NAME LIKE %(search)s OR a.PHONE LIKE %(search)s)"
        params['search'] = f'%{search_query}%'

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND a.SECTION_NAME = %(branch)s"
        params['branch'] = selected_branch

    if start_date and end_date:
        try:
            # Convert from HTML datetime-local format (with 'T' and possibly missing seconds)
            if 'T' in start_date:
                start_date = start_date.replace('T', ' ') + ':00'
            if 'T' in end_date:
                end_date = end_date.replace('T', ' ') + ':00'

            dt_format = '%Y-%m-%d '
            start_date_obj = datetime.strptime(start_date, dt_format)
            end_date_obj = datetime.strptime(end_date, dt_format)

            query += """
            AND b.ATTENDANCE_DATE 
            BETWEEN %(start_date)s 
            AND %(end_date)s
            """
            params['start_date'] = start_date_obj.strftime(dt_format)
            params['end_date'] = end_date_obj.strftime(dt_format)

        except ValueError:
            return "Invalid datetime format. Please use YYYY-MM-DDTHH%(MM)s from input."


    # Finalize query order
    query += " ORDER BY FULL_NAME,ATTENDANCE_DATE"

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()  # Now this contains only filtered results

    # Pagination logic
    total = len(filtered_records)  # Total number of filtered records
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    payments_paginated = filtered_records[start:end]

    # Export functionality: pass the filtered data (filtered_records) to export functions
    if export_format == 'csv':
        return export_attendance_csv(filtered_records)  # Export filtered data
    elif export_format == 'pdf':
        return attendance_report_pdf(filtered_records)  # Export filtered data
    elif export_format == 'excel':
        return attendance_report_excel(filtered_records)  # Export filtered data

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches()
    branches = get_members()

    # Render the template and pass paginated payments data
    return render_template(
        'attendance_report.html',
        payments=payments_paginated,
        search_query=search_query,
        branches=branches,
        selected_branch=selected_branch,
        start_date=start_date,
        end_date=end_date,
        page=page,
        pages=pages
    )





@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')




from collections import namedtuple

def make_named_tuple(cursor):
    fields = [col[0] for col in cursor.description]
    Row = namedtuple('Row', fields)
    return Row

@app.route('/user_management')
@login_required
# @login_required
@role_required('Super Admin') 
# @login_required
# @role_required('Super Admin')
def user_management():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT u.USER_ID, u.USERNAME, u.PAYROLL_NUMBER, u.BRANCH, 
               r.ROLE_ID, r.ROLE_NAME
        FROM AAWSA_USER u
        JOIN ROLES r ON u.ROLE_ID = r.ROLE_ID
        ORDER BY u.USERNAME
    """)
    
    # Convert to named tuples
    users = [make_named_tuple(cursor)(*row) for row in cursor]
    
    cursor.execute("SELECT ROLE_ID, ROLE_NAME FROM ROLES ORDER BY ROLE_NAME")
    roles = [make_named_tuple(cursor)(*row) for row in cursor]
    
    cursor.close()
    conn.close()
    
    return render_template('user_management.html', users=users, roles=roles)


# Create User
@app.route('/create_user', methods=['POST'])
# @login_required
# # @login_required
# @role_required('Super Admin') 
# @login_required
# @role_required('Super Admin')
def create_user():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    form_data = {
        'username': request.form['username'],
        'password': generate_password_hash(request.form['password']),  # Hashed password
        'payroll_number': request.form['payroll_number'],
        'branch': request.form['branch'],
        'role_id': request.form['role_id']
    }
    
    try:
        # Check if username or payroll number exists
        cursor.execute("""
            SELECT 1 FROM aawsa_user 
            WHERE username = %(username)s OR payroll_number = %(payroll_number)s
        """, {'username': form_data['username'], 'payroll_number': form_data['payroll_number']})
        
        if cursor.fetchone():
            flash('Username or payroll number already exists!', 'danger')
        else:
            # Verify role exists
            cursor.execute("SELECT 1 FROM roles WHERE role_id = %(role_id)s", {'role_id': form_data['role_id']})
            if not cursor.fetchone():
                flash('Invalid role selected!', 'danger')
            else:
                # Insert new user
                cursor.execute("""
                    INSERT INTO aawsa_user (username, password, payroll_number, branch, role_id)
                    VALUES (%(username)s, %(password)s, %(payroll_number)s, %(branch)s, %(role_id)s)
                """, form_data)
                conn.commit()
                flash('User created successfully!', 'success')
                print(request.form)  # In your create_user route
    except Exception as e:
        conn.rollback()
        flash(f'Error creating user: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('user_management'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
# @login_required
@role_required('Super Admin') 
# @login_required
# @role_required('Super Admin')
def edit_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form['username']
            payroll_number = request.form['payroll_number']
            branch = request.form['branch']
            role_id = request.form['role_id']
            
            # Update user
            cursor.execute("""
                UPDATE aawsa_user 
                SET username = %(username)s,
                    payroll_number = %(payroll_number)s,
                    branch = %(branch)s,
                    role_id = %(role_id)s
                WHERE user_id = %(user_id)s
            """, {
                'username': username,
                'payroll_number': payroll_number,
                'branch': branch,
                'role_id': role_id,
                'user_id': user_id
            })
            conn.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('user_management'))
        except Exception as e:
            conn.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
    
    # GET request - load user data
    try:
        # Get user data (returns as tuple)
        cursor.execute("""
            SELECT user_id, username, payroll_number, branch, role_id
            FROM aawsa_user
            WHERE user_id = %(user_id)s
        """, {'user_id': user_id})
        user_tuple = cursor.fetchone()
        
        if not user_tuple:
            flash('User not found!', 'danger')
            return redirect(url_for('user_management'))
        
        # Convert tuple to dictionary for easier template access
        user = {
            'user_id': user_tuple[0],
            'username': user_tuple[1],
            'payroll_number': user_tuple[2],
            'branch': user_tuple[3],
            'role_id': user_tuple[4]
        }
        
        # Get all roles
        cursor.execute("SELECT role_id, role_name FROM roles ORDER BY role_name")
        roles_tuples = cursor.fetchall()
        
        # Convert roles tuples to dictionaries
        roles = [{'role_id': r[0], 'role_name': r[1]} for r in roles_tuples]
        
        return render_template('edit_user.html', user=user, roles=roles)
    except Exception as e:
        flash(f'Error loading user data: {str(e)}', 'danger')
        return redirect(url_for('user_management'))
    finally:
        cursor.close()
        conn.close()

# Delete User
@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
# @login_required
@role_required('Super Admin') 
# @login_required
# @role_required('Super Admin')
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM aawsa_user WHERE user_id = %(user_id)s", {'user_id': user_id})
        conn.commit()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('user_management'))

@app.route('/show_users')
@login_required
# @login_required
@role_required('Super Admin') 
def show_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.payroll_number, u.payroll_number, b.branch_name, r.role_name
        FROM aawsa_user u
        JOIN branch b ON u.user_id = b.user_id
        JOIN role r ON u.user_id = r.user_id
    """)
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('show_users.html', users=users)


@app.route('/upload_member_registration', methods=['GET', 'POST'])
def upload_member_registration():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.csv'):
            flash("Please upload a valid CSV file.", "warning")
            return redirect(url_for('upload_member_registration'))

        import csv
        import io

        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            for row in csv_input:
                cursor.execute("""
                    INSERT INTO member_registration (
                        full_name, father_of_repentance, mother_name, parish, christian_name,
                        age_of_birth, subcity, woreda, house_number, special_place,
                        phone, leving, work_status, email, member_year,
                        education, `rank`, education_status, work, student,
                        career, marital_status
                    ) VALUES (
                        %(full_name)s, %(father_of_repentance)s, %(mother_name)s, %(parish)s, %(christian_name)s,
                        %(age_of_birth)s, %(subcity)s, %(woreda)s, %(house_number)s, %(special_place)s,
                        %(phone)s, %(leving)s, %(work_status)s, %(email)s, %(member_year)s,
                        %(education)s, %(rank)s, %(education_status)s, %(work)s, %(student)s,
                        %(career)s, %(marital_status)s
                    )
                """, row)
            conn.commit()
            flash("Member registration data uploaded successfully!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Failed to upload data: {str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('upload_member_registration'))

    return render_template('upload_member_registration.html')

@app.route('/manage_members', methods=['GET', 'POST'])
def manage_members():
    conn = get_db_connection()
    cursor = conn.cursor()
    member_data = {}

    if request.method == 'POST':
        form_data = request.form.to_dict()

        # Rename spiritual_education -> education
        form_data['education'] = form_data.pop('spiritual_education', None)

        # If ID is not provided, make sure it's not in the dict
        member_id = form_data.get('id')
        if not member_id:
            form_data.pop('id', None)

        if member_id:  # UPDATE
            query = """
                UPDATE member_registration SET
                    full_name=%(full_name)s,
                    father_of_repentance=%(father_of_repentance)s,
                    mother_name=%(mother_name)s,
                    parish=%(parish)s,
                    christian_name=%(christian_name)s,
                    age_of_birth=%(age_of_birth)s,
                    subcity=%(subcity)s,
                    woreda=%(woreda)s,
                    house_number=%(house_number)s,
                    special_place=%(special_place)s,
                    phone=%(phone)s,
                    leving=%(leving)s,
                    work_status=%(work_status)s,
                    email=%(email)s,
                    member_year=%(member_year)s,
                    education=%(education)s,
                    `rank`=%(rank)s,
                    education_status=%(education_status)s,
                    work=%(work)s,
                    student=%(student)s,
                    career=%(career)s,
                    marital_status=%(marital_status)s,
                    section_name=%(section_name)s,
                    gender=%(gender)s
                WHERE id=%(id)s
            """
        else:  # INSERT
            query = """
                INSERT INTO member_registration (
                    full_name, father_of_repentance, mother_name, parish, christian_name,
                    age_of_birth, subcity, woreda, house_number, special_place,
                    phone, leving, work_status, email, member_year, education,
                    `rank`, education_status, work, student, career, marital_status,section_name,gender
                ) VALUES (
                    %(full_name)s, %(father_of_repentance)s, %(mother_name)s, %(parish)s, %(christian_name)s,
                    %(age_of_birth)s, %(subcity)s, %(woreda)s, %(house_number)s, %(special_place)s,
                    %(phone)s, %(leving)s, %(work_status)s, %(email)s, %(member_year)s, %(education)s,
                    %(rank)s, %(education_status)s, %(work)s, %(student)s, %(career)s, %(marital_status)s, %(section_name)s, %(gender)s
                )
            """

        try:
            cursor.execute(query, form_data)
            conn.commit()
            flash("Member saved successfully.", "success")
            return redirect(url_for('manage_members'))
        except Exception as e:
            flash(f"Database Error: {str(e)}", "danger")

    # DELETE
    delete_id = request.args.get('delete')
    if delete_id:
        try:
            cursor.execute("DELETE FROM member_registration WHERE id = %(id)s", {'id': delete_id})
            conn.commit()
            flash("Member deleted.", "info")
            return redirect(url_for('manage_members'))
        except Exception as e:
            flash(f"Error deleting member: {str(e)}", "danger")

    # EDIT
    edit_id = request.args.get('edit')
    if edit_id:
        cursor.execute("SELECT * FROM member_registration WHERE id = %(id)s", {'id': edit_id})
        row = cursor.fetchone()
        if row:
            col_names = [desc[0].lower() for desc in cursor.description]
            member_data = dict(zip(col_names, row))

    # LAST 10
    cursor.execute("""
        SELECT * FROM member_registration 
        ORDER BY id DESC 
        LIMIT 10
    """)
    rows = cursor.fetchall()
    col_names = [desc[0].lower() for desc in cursor.description]
    members = [dict(zip(col_names, row)) for row in rows]

    cursor.close()
    conn.close()

    return render_template("manage_members.html", members=members, member_data=member_data)


@app.route('/member_report')
def member_report():
    """Comprehensive member report with statistics and charts"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get filters
    section_filter = request.args.get('section', '')
    gender_filter = request.args.get('gender', '')
    year_filter = request.args.get('year', datetime.now().year)
    
    # Overall statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_members,
            COUNT(CASE WHEN gender = 'ወንድ' THEN 1 END) as male_count,
            COUNT(CASE WHEN gender = 'ሴት' THEN 1 END) as female_count,
            COUNT(CASE WHEN marital_status IN ('ያላገባ', 'ያላገባች') THEN 1 END) as single_count,
            COUNT(CASE WHEN marital_status = 'ያገባ' THEN 1 END) as married_count,
            COUNT(CASE WHEN work_status = 'በሥራ ላይ' THEN 1 END) as employed_count,
            COUNT(CASE WHEN work_status = 'ስራ የለኝም' THEN 1 END) as unemployed_count,
            COUNT(CASE WHEN work_status = 'ተማሪ' OR student = 'Yes' THEN 1 END) as student_count
        FROM member_registration
    """)
    stats = cursor.fetchone()
    overall_stats = {
        'total_members': stats[0] or 0,
        'male_count': stats[1] or 0,
        'female_count': stats[2] or 0,
        'single_count': stats[3] or 0,
        'married_count': stats[4] or 0,
        'employed_count': stats[5] or 0,
        'unemployed_count': stats[6] or 0,
        'student_count': stats[7] or 0
    }
    
    # Section-wise statistics
    cursor.execute("""
        SELECT 
            section_name,
            COUNT(*) as total,
            COUNT(CASE WHEN gender = 'ወንድ' THEN 1 END) as male,
            COUNT(CASE WHEN gender = 'ሴት' THEN 1 END) as female
        FROM member_registration
        GROUP BY section_name
        ORDER BY section_name
    """)
    section_stats = cursor.fetchall()
    
    # Age distribution (approximate)
    cursor.execute("""
        SELECT 
            CASE 
                WHEN TIMESTAMPDIFF(YEAR, age_of_birth, CURDATE()) < 18 THEN 'Under 18'
                WHEN TIMESTAMPDIFF(YEAR, age_of_birth, CURDATE()) BETWEEN 18 AND 30 THEN '18-30'
                WHEN TIMESTAMPDIFF(YEAR, age_of_birth, CURDATE()) BETWEEN 31 AND 50 THEN '31-50'
                WHEN TIMESTAMPDIFF(YEAR, age_of_birth, CURDATE()) > 50 THEN 'Over 50'
                ELSE 'Unknown'
            END as age_group,
            COUNT(*) as count
        FROM member_registration
        WHERE age_of_birth IS NOT NULL
        GROUP BY age_group
        ORDER BY age_group
    """)
    age_distribution = cursor.fetchall()
    
    # Education statistics
    cursor.execute("""
        SELECT 
            education_status,
            COUNT(*) as count
        FROM member_registration
        WHERE education_status IS NOT NULL AND education_status != ''
        GROUP BY education_status
        ORDER BY count DESC
    """)
    education_stats = cursor.fetchall()
    
    # Subcity distribution
    cursor.execute("""
        SELECT 
            subcity,
            COUNT(*) as count
        FROM member_registration
        WHERE subcity IS NOT NULL AND subcity != ''
        GROUP BY subcity
        ORDER BY count DESC
        LIMIT 10
    """)
    subcity_stats = cursor.fetchall()
    
    # Build filtered query for detailed list
    query = """
        SELECT id, full_name, gender, section_name, phone, email, 
               subcity, marital_status, work_status, education_status
        FROM member_registration
        WHERE 1=1
    """
    params = []
    
    if section_filter:
        query += " AND section_name = %s"
        params.append(section_filter)
    
    if gender_filter:
        query += " AND gender = %s"
        params.append(gender_filter)
    
    query += " ORDER BY section_name, full_name LIMIT 100"
    
    cursor.execute(query, params)
    members_list = cursor.fetchall()
    
    sections = ['የሕፃናት ክፍል', 'ማህከላዊያን ክፍል', 'ወጣት ክፍል', 'ወላጅ ክፍል']
    
    cursor.close()
    conn.close()
    
    return render_template('member_report.html',
                         overall_stats=overall_stats,
                         section_stats=section_stats,
                         age_distribution=age_distribution,
                         education_stats=education_stats,
                         subcity_stats=subcity_stats,
                         members_list=members_list,
                         sections=sections,
                         section_filter=section_filter,
                         gender_filter=gender_filter,
                         year_filter=year_filter)


def get_last_10_weeks_weekends():
    today = date.today()
    dates = []
    days_back = 70
    for i in range(days_back):
        day = today - timedelta(days=i)
        if day.weekday() in (5, 6):  # Saturday or Sunday
            dates.append(day.strftime('%Y-%m-%d'))
            if len(dates) >= 20:
                break
    dates.sort()
    return dates

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch distinct section names for dropdown
    cursor.execute("SELECT DISTINCT section_name FROM member_registration ORDER BY section_name")
    section_names = [row[0] for row in cursor.fetchall()]

    selected_section = request.args.get('section')

    if request.method == 'POST':
        # On submit, section name comes as hidden input
        selected_section = request.form.get('selected_section')
        form_data = request.form.to_dict()
        try:
            for key, value in form_data.items():
                if not key.startswith('attendance_'):
                    continue
                if value == '':
                    continue
                _, member_id_str, att_date_str = key.split('_', 2)
                member_id = int(member_id_str)
                attendance_date = att_date_str
                present_status = value
                day_name = date.fromisoformat(attendance_date).strftime('%A')
                remarks = ''

                cursor.execute("""
                    SELECT id FROM attendance 
                    WHERE member_id = %(member_id)s AND DATE(attendance_date) = %(attendance_date)s
                """, {'member_id': member_id, 'attendance_date': attendance_date})
                row = cursor.fetchone()

                if row:
                    cursor.execute("""
                        UPDATE attendance SET
                            present_status = %(present_status)s,
                            day_name = %(day_name)s,
                            remarks = %(remarks)s
                        WHERE id = %(id)s
                    """, {'present_status': present_status, 'day_name': day_name, 'remarks': remarks, 'id': row[0]})
                else:
                    cursor.execute("""
                        INSERT INTO attendance (
                            member_id, attendance_date, present_status, day_name, remarks
                        ) VALUES (
                            %(member_id)s, %(attendance_date)s, %(present_status)s, %(day_name)s, %(remarks)s
                        )
                    """, {'member_id': member_id, 'attendance_date': attendance_date, 'present_status': present_status, 'day_name': day_name, 'remarks': remarks})
            conn.commit()
            flash("Attendance saved successfully.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error saving attendance: {e}", "danger")
        return redirect(url_for('attendance', section=selected_section))

    members = []
    attendance_data = {}
    dates = []

    if selected_section:
        # Fetch members only in selected section
        cursor.execute("""
            SELECT id, full_name FROM member_registration WHERE section_name = %(section)s ORDER BY full_name
        """, {'section': selected_section})
        members_rows = cursor.fetchall()
        members = [{'member_id': m[0], 'full_name': m[1]} for m in members_rows]

        # Dates for attendance
        dates = get_last_10_weeks_weekends()

        if members:
            member_ids = [m['member_id'] for m in members]
            format_ids = ",".join(str(id) for id in member_ids)
            format_dates = ",".join(f"'{d}'" for d in dates)

            query = f"""
                SELECT member_id, DATE_FORMAT(attendance_date, '%Y-%m-%d') AS att_date, present_status
                FROM attendance
                WHERE member_id IN ({format_ids})
                  AND DATE(attendance_date) IN ({format_dates})
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            attendance_data = {f"{r[0]}_{r[1]}": r[2] for r in rows}

    cursor.close()
    conn.close()

    return render_template('attendance_section.html',
                           section_names=section_names,
                           selected_section=selected_section,
                           members=members,
                           dates=dates,
                           attendance_data=attendance_data)
@app.template_filter('durationformat')
def durationformat(value):
    if not value:
        return '0s'
    try:
        seconds = int(value.total_seconds())
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds or not parts:
            parts.append(f"{seconds}s")
        return ' '.join(parts)
    except Exception:
        return str(value)
@app.template_filter('currencyformat')
def currencyformat(value):
    try:
        return "{:,.2f}".format(float(value))  # Add commas and 2 decimal places
    except (ValueError, TypeError):
        return value


@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.strftime(format)
    try:
        # If value is string or timestamp
        dt = datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')
        return dt.strftime(format)
    except Exception:
        return value


@app.route('/logout')
def logout():
    session.pop('payroll_number', None)  # Remove payroll_number from the session
    return redirect(url_for('login'))  # Redirect to the login page

if __name__ == '__main__':
    app.run(debug=True,port=5001,host="0.0.0.0")
