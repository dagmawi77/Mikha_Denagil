import math
from flask import Flask, Response, render_template, request, redirect, url_for, session, flash, send_file, make_response
import cx_Oracle
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



app = Flask(__name__)


#app.run(host='0.0.0.0',port=5001,debug=True)
app.secret_key = 'your_secret_key'  # Change this to a secure key
app.permanent_session_lifetime = timedelta(minutes=3)  # Set session timeout to 3 minutes
def get_db_connection():
    conn = cx_Oracle.connect('aawsa_api/aawsa_api@localhost:1522/aawsa_api')
    # conn = cx_Oracle.connect('aawsa_api/aawsa_api@10.12.110.76:1521/apiaawsa')
    return conn

def get_db_connection_billing():
    conn_bill = cx_Oracle.connect('apps/ndf36fgn@10.12.110.14:1522/basis2db.aawsa.local')
    return conn_bill
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
                    WHERE u.payroll_number = :payroll_number
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
                WHERE u.payroll_number = :payroll_number
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
            WHERE u.payroll_number = :payroll_number
        """, {"payroll_number": payroll_number})
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[2], password):  # Or better: user['password']
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
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if tables exist first
        cursor.execute("""
        DECLARE
            v_count NUMBER;
        BEGIN
            SELECT COUNT(*) INTO v_count FROM user_tables WHERE table_name = 'ROLES';
            IF v_count = 0 THEN
                EXECUTE IMMEDIATE 'CREATE TABLE roles (
                    role_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    role_name VARCHAR2(100) NOT NULL UNIQUE,
                    description VARCHAR2(255)
                )';
            END IF;
            
            SELECT COUNT(*) INTO v_count FROM user_tables WHERE table_name = 'ROUTES';
            IF v_count = 0 THEN
                EXECUTE IMMEDIATE 'CREATE TABLE routes (
                    route_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    route_name VARCHAR2(100) NOT NULL UNIQUE,
                    endpoint VARCHAR2(255) NOT NULL UNIQUE,
                    description VARCHAR2(255)
                )';
            END IF;
            
            SELECT COUNT(*) INTO v_count FROM user_tables WHERE table_name = 'ROLE_ROUTES';
            IF v_count = 0 THEN
                EXECUTE IMMEDIATE 'CREATE TABLE role_routes (
                    role_id NUMBER NOT NULL,
                    route_id NUMBER NOT NULL,
                    PRIMARY KEY (role_id, route_id),
                    FOREIGN KEY (role_id) REFERENCES roles(role_id),
                    FOREIGN KEY (route_id) REFERENCES routes(route_id)
                )';
            END IF;
            
            -- Check if column exists before adding
            SELECT COUNT(*) INTO v_count FROM user_tab_columns 
            WHERE table_name = 'AAWSA_USER' AND column_name = 'ROLE_ID';
            IF v_count = 0 THEN
                EXECUTE IMMEDIATE 'ALTER TABLE aawsa_user ADD (role_id NUMBER)';
                EXECUTE IMMEDIATE 'ALTER TABLE aawsa_user ADD CONSTRAINT fk_user_role 
                                  FOREIGN KEY (role_id) REFERENCES roles(role_id)';
            END IF;
        END;
        """)
        conn.commit()
        print("RBAC tables initialized/verified")
    except Exception as e:
        conn.rollback()
        print(f"Error initializing RBAC tables: {str(e)}")
    finally:
        cursor.close()
        conn.close()

# Call this at application startup
initialize_rbac_tables()
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
                WHERE u.payroll_number = :payroll_number
                ORDER BY r.route_name
            """, {'payroll_number': session['payroll_number']})
            return cursor.fetchall()
        except cx_Oracle.DatabaseError as e:
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
            WHERE rr.role_id = :role_id
        """, {'role_id': role_id})
        routes = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return routes
    return dict(get_assigned_routes=get_assigned_routes)

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
            VALUES (:role_name, :description)
        """, {'role_name': role_name, 'description': description})
        conn.commit()
        flash('Role created successfully!', 'success')
    except cx_Oracle.DatabaseError as e:
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
        cursor.execute("DELETE FROM role_routes WHERE role_id = :role_id", 
                      {'role_id': role_id})
        
        # Add the new selected routes
        for route_id in selected_routes:
            cursor.execute("""
                INSERT INTO role_routes (role_id, route_id)
                VALUES (:role_id, :route_id)
            """, {'role_id': role_id, 'route_id': route_id})
        
        conn.commit()
        flash('Route permissions updated successfully!', 'success')
    except cx_Oracle.DatabaseError as e:
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
        cursor.execute("SELECT COUNT(*) FROM aawsa_user WHERE role_id = :role_id", 
                      {'role_id': role_id})
        user_count = cursor.fetchone()[0]
        
        if user_count > 0:
            flash('Cannot delete role - there are users assigned to it!', 'danger')
        else:
            # Delete role routes first
            cursor.execute("DELETE FROM role_routes WHERE role_id = :role_id", 
                          {'role_id': role_id})
            # Then delete the role
            cursor.execute("DELETE FROM roles WHERE role_id = :role_id", 
                          {'role_id': role_id})
            conn.commit()
            flash('Role deleted successfully!', 'success')
    except cx_Oracle.DatabaseError as e:
        conn.rollback()
        flash(f'Error deleting role: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('manage_roles'))

def initialize_default_roles_and_routes():
    conn = get_db_connection()
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
                INSERT INTO roles (role_name, description)
                VALUES (:role_name, :description)
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
                INSERT INTO routes (route_name, endpoint, description)
                VALUES (:route_name, :endpoint, :description)
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
                INSERT INTO role_routes (role_id, route_id)
                VALUES (:role_id, :route_id)
            """, {'role_id': super_admin_id, 'route_id': route_id})
        
        conn.commit()
        print("Default roles and routes initialized successfully")
    except Exception as e:
        conn.rollback()
        print(f"Error initializing default roles and routes: {str(e)}")
    finally:
        cursor.close()
        conn.close()

# Call this function once when setting up your application
initialize_default_roles_and_routes()

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
            cursor.execute("DELETE FROM role_routes WHERE role_id = :role_id", {'role_id': role_id})
            
            # Add the new selected routes
            for route_id in selected_routes:
                cursor.execute("""
                    INSERT INTO role_routes (role_id, route_id)
                    VALUES (:role_id, :route_id)
                """, {'role_id': role_id, 'route_id': route_id})
            
            conn.commit()
            flash('Route permissions updated successfully!', 'success')
        except cx_Oracle.DatabaseError as e:
            conn.rollback()
            flash(f'Error updating route permissions: {str(e)}', 'danger')
        
        return redirect(url_for('manage_role_routes', role_id=role_id))
    
    # GET request - show current routes and available routes
    # Get role info
    cursor.execute("SELECT role_name FROM roles WHERE role_id = :role_id", {'role_id': role_id})
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
        WHERE rr.role_id = :role_id
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
                VALUES (:route_name, :endpoint, :description)
            """, {
                'route_name': route_name,
                'endpoint': endpoint,
                'description': description
            })
            conn.commit()
            flash('Route added successfully!', 'success')
        except cx_Oracle.DatabaseError as e:
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
        cursor = connection.cursor()
        
        # Query for recent sent bills
        cursor.execute("""
            SELECT b.BILLKEY, b.CUSTOMERNAME, b.TOTALBILLAMOUNT, p.AMOUNT, p.PAYMENTCOMPLETEDAT
            FROM BILL b
            JOIN PAYMENT p ON b.BILLKEY = p.BILLKEY
            
            ORDER BY p.PAYMENTCOMPLETEDAT DESC
            FETCH FIRST 10 ROWS ONLY
        """)
        recent_sent_bills = cursor.fetchall() or []  # Default to empty list if None

        cursor.execute("""
                    
    select CUSTOMERBRANCH,REASON,count(*) number_bill,TO_CHAR(sum(CONS),'FM999,999,999'),TO_CHAR(sum(THISMONTHBILLAMT),'FM999,999,999') current_bill 
    ,TO_CHAR(sum(OUTSTANDINGAMT),'FM999,999,999') outstanding_bill ,TO_CHAR(sum(TOTALBILLAMOUNT),'FM999,999,999') total_bill_amount from bill 
    where billkey in (select billkey from payment) and  REASON!='March-2025' group by CUSTOMERBRANCH,REASON order by 
    TOTAL_BILL_AMOUNT desc
        """)
        current_settled = cursor.fetchall() or []
        cursor.execute("""
                    
    select CUSTOMERBRANCH,REASON,count(*) number_bill,TO_CHAR(sum(CONS),'FM999,999,999'),TO_CHAR(sum(THISMONTHBILLAMT),'FM999,999,999') current_bill 
    ,TO_CHAR(sum(OUTSTANDINGAMT),'FM999,999,999') outstanding_bill ,TO_CHAR(sum(TOTALBILLAMOUNT),'FM999,999,999') total_bill_amount from bill 
    where   REASON!='March-2025' group by CUSTOMERBRANCH,REASON order by 
    TOTAL_BILL_AMOUNT desc
        """)
        current_delivery = cursor.fetchall() or []
        cursor.execute("""
                    
    select CUSTOMERBRANCH,REASON,count(*) number_bill,TO_CHAR(sum(CONS),'FM999,999,999'),TO_CHAR(sum(THISMONTHBILLAMT),'FM999,999,999') current_bill 
    ,TO_CHAR(sum(OUTSTANDINGAMT),'FM999,999,999') outstanding_bill ,TO_CHAR(sum(TOTALBILLAMOUNT),'FM999,999,999') total_bill_amount from bill 
    where  billkey not in (select billkey from payment) and REASON!='March-2025' group by CUSTOMERBRANCH,REASON order by 
    TOTAL_BILL_AMOUNT desc
        """)
        current_unsettled = cursor.fetchall() or []
        # Query for bill statistics
        cursor.execute(""" 
            select TO_CHAR(Count(*),'FM999,999,999'),
                   TO_CHAR(Count(*),'FM999,999,999') as TOTALBILLAMOUNT,
                   TO_CHAR(Count(*),'FM999,999,999') as THISMONTHBILLAMT  
            from MEMBER_REGISTRATION 
            group by REASON
        """)
        total_bills_result = cursor.fetchone()
        if total_bills_result:
            total_bills = list(total_bills_result)
            # Convert formatted strings back to numbers for calculations
           # total_bills[0] = int(total_bills[0].replace(',', '')) if total_bills[0] else 0
           # total_bills[2] = float(total_bills[2].replace(',', '')) if total_bills[2] else 0
           # total_bills[3] = float(total_bills[3].replace(',', '')) if total_bills[3] else 0

        # Query for payment statistics
        cursor.execute(""" 
            select TO_CHAR(count(*),'FM999,999,999') no_bills,REASON,
                   TO_CHAR(sum(TOTALBILLAMOUNT),'999,999,999.00') as TOTALBILLAMOUNT,
                   TO_CHAR(sum(THISMONTHBILLAMT),'999,999,999.00') THISMONTHBILLAMT 
            from payment a, bill b 
            where a.billkey = b.billkey 
            group by REASON  
        """)
        payment_result = cursor.fetchone()
        if payment_result:
            payment_total = list(payment_result)
           # payment_total[0] = int(payment_total[0].replace(',', '')) if payment_total[0] else 0
           # payment_total[2] = float(payment_total[2].replace(',', '')) if payment_total[2] else 0
            #payment_total[3] = float(payment_total[3].replace(',', '')) if payment_total[3] else 0

        # Query for sent vs paid comparison
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN p.PAYMENTDATE IS NOT NULL THEN p.AMOUNT ELSE 0 END), 0) AS total_paid_amount,
                COALESCE(SUM(b.TOTALBILLAMOUNT), 0) AS total_sent_amount,
                COALESCE((COUNT(b.BILLKEY) - COUNT(DISTINCT p.BILLKEY)), 0) AS number_sent,
                COALESCE(COUNT(DISTINCT p.BILLKEY), 0) AS number_paid
            FROM BILL b
            LEFT JOIN PAYMENT p ON b.BILLKEY = p.BILLKEY
        """)
        comparison_result = cursor.fetchone()
        if comparison_result:
            comparison = list(comparison_result)

        # Query for branch-based sent data
        cursor.execute("""
            SELECT SECTION_NAME as PAYMENTCHANNEL
    , count(*) AS total_amount
            FROM MEMBER_REGISTRATION p
            GROUP BY p.SECTION_NAME
        """)
        branch_stats = cursor.fetchall() or []

        # Query for payment channels
        cursor.execute("""
             SELECT SECTION_NAME as PAYMENTCHANNEL
    , count(*) AS total_amount
            FROM MEMBER_REGISTRATION p
            GROUP BY p.SECTION_NAME

        """)
        payment_by_channel = cursor.fetchall() or []
        
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
        # cursor.execute(""" 
        #     SELECT count(*),SECTION_NAME
        #     FROM MEMBER_REGISTRATION  where SECTION_NAME='የሕፃናት ክፍል'
        #                group by  SECTION_NAME
        # """)
        # total_bills = cursor.fetchone()
        # if total_bills:
        #     data.update({
        #         'current_month_total_bill_amnt': total_bills[0],
        #         'current_month_bill_amnt': total_bills[2]

        #     })


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

@app.route('/export', methods=['GET'])
@login_required
# @login_required
@role_required('Super Admin') 
def export_form():
    # Fetch available branches and periods from the database
    branches = []
    periods = []
    
    with get_db_connection_billing() as conn:
        cursor = conn.cursor()
        
        # Fetch distinct branches
        cursor.execute("SELECT DISTINCT branch FROM AAWSA_List_of_branch")
        branches = cursor.fetchall()
        
        # Fetch distinct periods
        cursor.execute("SELECT DISTINCT period FROM AAWSA_List_of_period")
        periods = cursor.fetchall()
    
    return render_template('old_delivery.html', branches=branches, periods=periods)

@app.route('/export', methods=['POST'])
@login_required
def export_data():
    # Access form data safely
    branch = request.form.get('branch')
    period = request.form.get('period')
    file_format = request.form.get('file_format')

    # Check if all required fields are provided
    if not branch or not period or not file_format:
        return "All fields are required.", 400

    # Query the database for the selected branch and period
    query = """
    SELECT * FROM aawsa_2021all_delivery
    WHERE branch = :branch AND period = :period
    """
    
    with get_db_connection_billing() as conn:
        data = pd.read_sql(query, conn, params={'branch': branch, 'period': period})

    # Determine the file format and export accordingly
    if file_format == 'csv':
        output_file = f"{branch}_bills_{period}.csv"
        data.to_csv(output_file, index=False)
        return send_file(output_file, as_attachment=True)
    
    elif file_format == 'excel':
        output_file = f"{branch}_bills_{period}.xlsx"
        data.to_excel(output_file, index=False)
        return send_file(output_file, as_attachment=True)

    return "Invalid file format", 400


@app.route('/export_settled', methods=['GET'])
@login_required
def export_form_settled():
    # Fetch available branches and periods from the database
    branches = []
    periods = []
    
    with get_db_connection_billing() as conn:
        cursor = conn.cursor()
        
        # Fetch distinct branches
        cursor.execute("SELECT DISTINCT branch FROM AAWSA_List_of_branch")
        branches = cursor.fetchall()
        
        # Fetch distinct periods
        cursor.execute("SELECT DISTINCT period FROM AAWSA_List_of_period")
        periods = cursor.fetchall()
    
    return render_template('old_settled.html', branches=branches, periods=periods)

@app.route('/export_settled', methods=['POST'])
@login_required
def export_data_settled():
    # Access form data safely
    branch = request.form.get('branch')
    period = request.form.get('period')
    file_format = request.form.get('file_format')

    # Check if all required fields are provided
    if not branch or not period or not file_format:
        return "All fields are required.", 400

    # Query the database for the selected branch and period
    query = """
    SELECT * FROM aawsa_2021all_delivery
    WHERE branch = :branch AND period = :period and bill_key in (select bill_key from aawsa_2021all_settled)
    """
    
    with get_db_connection_billing() as conn:
        data = pd.read_sql(query, conn, params={'branch': branch, 'period': period})

    # Determine the file format and export accordingly
    if file_format == 'csv':
        output_file = f"{branch}_bills_{period}.csv"
        data.to_csv(output_file, index=False)
        return send_file(output_file, as_attachment=True)
    
    elif file_format == 'excel':
        output_file = f"{branch}_bills_{period}.xlsx"
        data.to_excel(output_file, index=False)
        return send_file(output_file, as_attachment=True)

    return "Invalid file format", 400




# @app.route('/export_delivery_cg', methods=['GET'])
# @login_required
# def export_form_delivery_cg():
#     # Fetch available branches and periods from the database
#     branches = []
#     periods = []
    
#     with get_db_connection_billing() as conn:
#         cursor = conn.cursor()
        
#         # Fetch distinct branches
#         cursor.execute("SELECT DISTINCT branch FROM dasbord_delivery_with_cg")
#         branches = cursor.fetchall()
        
#         # Fetch distinct periods
#         cursor.execute("SELECT DISTINCT period FROM dasbord_delivery_with_cg")
#         periods = cursor.fetchall()
    
#     return render_template('export_delivery_cg.html', branches=branches, periods=periods)

# @app.route('/export_delivery_cg', methods=['POST'])
# @login_required
# def export_data_delivery_cg():
#     # Access form data safely
#     branch = request.form.get('branch')
#     period = request.form.get('period')
#     file_format = request.form.get('file_format')

#     # Check if all required fields are provided
#     if not branch or not period or not file_format:
#         return "All fields are required.", 400

#     # Query the database for the selected branch and period
#     query = """
#     SELECT * FROM dasbord_delivery_with_cg
#     WHERE branch = :branch AND period = :period order by period,branch,ROUTE_KEY
#     """
    
#     with get_db_connection_billing() as conn:
#         data = pd.read_sql(query, conn, params={'branch': branch, 'period': period})

#     # Determine the file format and export accordingly
#     if file_format == 'csv':
#         output_file = f"{branch}_bills_{period}.csv"
#         data.to_csv(output_file, index=False)
#         return send_file(output_file, as_attachment=True)
    
#     elif file_format == 'excel':
#         output_file = f"{branch}_bills_{period}.xlsx"
#         data.to_excel(output_file, index=False)
#         return send_file(output_file, as_attachment=True)

#     return "Invalid file format", 400


@app.route('/export_delivery_cg', methods=['GET'])
@login_required
def export_form_delivery_cg():
    branches = []
    periods = []

    with get_db_connection_billing() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT branch FROM dasbord_delivery_with_cg where branch!='DT'")
        branches = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT period FROM dasbord_delivery_with_cg where branch!='DT'")
        periods = [row[0] for row in cursor.fetchall()]

    # Insert 'All' at the beginning
    branches.insert(0, 'All')
    periods.insert(0, 'All')

    return render_template('export_delivery_cg.html', branches=branches, periods=periods)
@app.route('/export_delivery_cg', methods=['POST'])
@login_required
def export_data_delivery_cg():
    branch = request.form.get('branch')
    period = request.form.get('period')
    file_format = request.form.get('file_format')

    if not branch or not period or not file_format:
        return "All fields are required.", 400

    # Base query
    query = "SELECT * FROM dasbord_delivery_with_cg WHERE 1=1 and branch!='DT'"
    params = {}

    # Apply filters only if not 'All'
    if branch != 'All':
        query += " AND branch = :branch"
        params['branch'] = branch

    if period != 'All':
        query += " AND period = :period"
        params['period'] = period

    query += " ORDER BY period, branch, ROUTE_KEY"

    with get_db_connection_billing() as conn:
        data = pd.read_sql(query, conn, params=params)

    filename_prefix = f"{branch}_{period}".replace("All", "all")
    
    if file_format == 'csv':
        output_file = f"{filename_prefix}_delivery_with_book.csv"
        data.to_csv(output_file, index=False)
        return send_file(output_file, as_attachment=True)

    elif file_format == 'excel':
        output_file = f"{filename_prefix}_delivery_with_book.xlsx"
        data.to_excel(output_file, index=False)
        return send_file(output_file, as_attachment=True)

    return "Invalid file format", 400





@app.route('/export_settled_cg', methods=['GET'])
@login_required
def export_form_settled_cg():
    branches = []
    periods = []

    with get_db_connection_billing() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT branch FROM dasbord_settled_with_cg where branch!='DT' ")
        branches = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT period FROM dasbord_settled_with_cg where branch!='DT'")
        periods = [row[0] for row in cursor.fetchall()]

    # Insert 'All' at the beginning
    branches.insert(0, 'All')
    periods.insert(0, 'All')

    return render_template('export_settled_cg.html', branches=branches, periods=periods)
@app.route('/export_settled_cg', methods=['POST'])
@login_required
def export_data_settled_cg():
    branch = request.form.get('branch')
    period = request.form.get('period')
    file_format = request.form.get('file_format')

    if not branch or not period or not file_format:
        return "All fields are required.", 400

    # Base query
    query = "SELECT * FROM dasbord_settled_with_cg WHERE 1=1  and branch!='DT'"
    params = {}

    # Apply filters only if not 'All'
    if branch != 'All':
        query += " AND branch = :branch"
        params['branch'] = branch

    if period != 'All':
        query += " AND period = :period"
        params['period'] = period

    query += " ORDER BY period, branch, ROUTE_KEY"

    with get_db_connection_billing() as conn:
        data = pd.read_sql(query, conn, params=params)

    filename_prefix = f"{branch}_{period}".replace("All", "all")
    
    if file_format == 'csv':
        output_file = f"{filename_prefix}_settled_with_book.csv"
        data.to_csv(output_file, index=False)
        return send_file(output_file, as_attachment=True)

    elif file_format == 'excel':
        output_file = f"{filename_prefix}_settled_with_book.xlsx"
        data.to_excel(output_file, index=False)
        return send_file(output_file, as_attachment=True)

    return "Invalid file format", 400




    
@app.route('/export_gl', methods=['GET'])
@login_required
def export_form_gl():
    branches = []
    periods = []

    with get_db_connection_billing() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT branch FROM dasbord_gl_detalis ")
        branches = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT period FROM dasbord_gl_detalis")
        periods = [row[0] for row in cursor.fetchall()]

    # Insert 'All' at the beginning
    branches.insert(0, 'All')
    periods.insert(0, 'All')

    return render_template('export_gl.html', branches=branches, periods=periods)
@app.route('/export_gl', methods=['POST'])
@login_required
def export_data_gl():
    branch = request.form.get('branch')
    period = request.form.get('period')
    file_format = request.form.get('file_format')

    if not branch or not period or not file_format:
        return "All fields are required.", 400

    # Base query
    query = "SELECT * FROM dasbord_gl_detalis WHERE 1=1 "
    params = {}

    # Apply filters only if not 'All'
    if branch != 'All':
        query += " AND branch = :branch"
        params['branch'] = branch

    if period != 'All':
        query += " AND period = :period"
        params['period'] = period

    query += " ORDER BY period, branch"

    with get_db_connection_billing() as conn:
        data = pd.read_sql(query, conn, params=params)

    filename_prefix = f"{branch}_{period}".replace("All", "all")
    
    if file_format == 'csv':
        output_file = f"{filename_prefix}_GL_detials.csv"
        data.to_csv(output_file, index=False)
        return send_file(output_file, as_attachment=True)

    elif file_format == 'excel':
        output_file = f"{filename_prefix}_GL_detials.xlsx"
        data.to_excel(output_file, index=False)
        return send_file(output_file, as_attachment=True)

    return "Invalid file format", 400





@app.route('/export_unsettled', methods=['GET'])
def export_form_unsettled():
    # Fetch available branches and periods from the database
    branches = []
    periods = []
    
    with get_db_connection_billing() as conn:
        cursor = conn.cursor()
        
        # Fetch distinct branches
        cursor.execute("SELECT DISTINCT branch FROM AAWSA_List_of_branch")
        branches = cursor.fetchall()
        
        # Fetch distinct periods
        cursor.execute("SELECT DISTINCT period from AAWSA_List_of_period")
        periods = cursor.fetchall()
    
    return render_template('old_settled.html', branches=branches, periods=periods)

@app.route('/export_unsettled', methods=['POST'])
@login_required
def export_data_unsettled():
    # Access form data safely
    branch = request.form.get('branch')
    period = request.form.get('period')
    file_format = request.form.get('file_format')

    # Check if all required fields are provided
    if not branch or not period or not file_format:
        return "All fields are required.", 400

    # Query the database for the selected branch and period
    query = """
    SELECT * FROM aawsa_2021all_delivery
    WHERE branch = :branch AND period = :period and bill_key not in (select bill_key from aawsa_2021all_settled)
    """
    
    with export_data_unsettled() as conn:
        data = pd.read_sql(query, conn, params={'branch': branch, 'period': period})

    # Determine the file format and export accordingly
    if file_format == 'csv':
        output_file = f"{branch}_bills_{period}.csv"
        data.to_csv(output_file, index=False)
        return send_file(output_file, as_attachment=True)
    
    elif file_format == 'excel':
        output_file = f"{branch}_bills_{period}.xlsx"
        data.to_excel(output_file, index=False)
        return send_file(output_file, as_attachment=True)

    return "Invalid file format", 400



@app.route('/list_sent_bills', methods=['GET', 'POST'])
@login_required
def list_sent_bills():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 300  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
     Select BILLKEY,
CUSTOMERKEY,
CUSTOMERNAME,
CUSTOMERTIN,
CUSTOMERBRANCH,
REASON,
CURRREAD,
PREVREAD,
CONS,
TOTALBILLAMOUNT,
THISMONTHBILLAMT,
OUTSTANDINGAMT,
PENALTYAMT,
DRACCTNO,
CRACCTNO from bill a
    """

    params = {}

    # Add search filter if search_query is provided
    if search_query:
        query += " WHERE (a.CUSTOMERKEY LIKE :search OR a.BILLKEY LIKE :search)"
        params['search'] = f'%{search_query}%'

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += "Where  a.CUSTOMERBRANCH = :branch"
        params['branch'] = selected_branch

    # Add date range filter if both start_date and end_date are provided
    # if start_date and end_date:
    #     query += """
    #     AND TO_DATE(SUBSTR(a.PAYMENTDATE, 1, 10), 'YYYY-MM-DD') 
    #     BETWEEN TO_DATE(:start_date, 'YYYY-MM-DD') 
    #     AND TO_DATE(:end_date, 'YYYY-MM-DD')
    #     """
    #     params['start_date'] = start_date  # Pass 'YYYY-MM-DD' formatted string
    #     params['end_date'] = end_date      # Pass 'YYYY-MM-DD' formatted string

    # Finalize query order

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    print(query)
    filtered_records = cursor.fetchall()  # Now this contains only filtered results
    # print(filtered_records)

    # Pagination logic
    total = len(filtered_records)  # Total number of filtered records
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    payments_paginated = filtered_records[start:end]

    # Export functionality: pass the filtered data (filtered_records) to export functions
    if export_format == 'csv':
        return export__delivery_csv(filtered_records)  # Export filtered data
    elif export_format == 'pdf':
        return export_delivery_pdf(filtered_records)  # Export filtered data
    elif export_format == 'excel':
        return export_delivery_excel(filtered_records)  # Export filtered data

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches()
    branches = get_branches()

    # Render the template and pass paginated payments data
    return render_template(
        'list_sent_bills.html',
        delivery=payments_paginated,
        search_query=search_query,
        branches=branches,
        selected_branch=selected_branch,
        # start_date=start_date,
        # end_date=end_date,
        page=page,
        pages=pages
    )



@app.route('/list_unmatched', methods=['GET', 'POST'])
@login_required
def list_unmatched():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('STATUS', 'All')  # Get the selected branch from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 300  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
     select BANKTXNREF,STATUS,MATCHED_AT,UPLOADED_BY,UPLOADED_AT from RECONCILIATION_RESULTS
    """

    params = {}

    # Add search filter if search_query is provided
   

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += "Where  STATUS = :STATUS"
        params['STATUS'] = selected_branch
  
        query += " and  BANKTXNREF LIKE :search_query"
        params['search_query'] = f"%{search_query}%"

    query += " ORDER BY UPLOADED_AT DESC"


    # Add date range filter if both start_date and end_date are provided
    # if start_date and end_date:
    #     query += """
    #     AND TO_DATE(SUBSTR(a.PAYMENTDATE, 1, 10), 'YYYY-MM-DD') 
    #     BETWEEN TO_DATE(:start_date, 'YYYY-MM-DD') 
    #     AND TO_DATE(:end_date, 'YYYY-MM-DD')
    #     """
    #     params['start_date'] = start_date  # Pass 'YYYY-MM-DD' formatted string
    #     params['end_date'] = end_date      # Pass 'YYYY-MM-DD' formatted string

    # Finalize query order

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    print(query)
    filtered_records = cursor.fetchall()  # Now this contains only filtered results
    # print(filtered_records)

    # Pagination logic
    total = len(filtered_records)  # Total number of filtered records
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    payments_paginated = filtered_records[start:end]

    # Export functionality: pass the filtered data (filtered_records) to export functions
    if export_format == 'csv':
        return export_csv(filtered_records)  # Export filtered data
    elif export_format == 'pdf':
        return export_pdf(filtered_records)  # Export filtered data
    elif export_format == 'excel':
        return export_excel(filtered_records)  # Export filtered data

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches()
    branches = get_branches()

    # Render the template and pass paginated payments data
    return render_template(
        'list_unmatched.html',
        delivery=payments_paginated,
        search_query=search_query,
        branches=branches,
        selected_branch=selected_branch,
        # start_date=start_date,
        # end_date=end_date,
        page=page,
        pages=pages
    )



@app.route('/list_unsettled_bills', methods=['GET', 'POST'])
@login_required
def list_unsettled_bills():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 300  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
     Select BILLKEY,
CUSTOMERKEY,
CUSTOMERNAME,
CUSTOMERTIN,
CUSTOMERBRANCH,
REASON,
route_key,charge_group,CONTRACT_NUMBER,METER_KEY, 
CURRREAD,
PREVREAD,
CONS,
TOTALBILLAMOUNT,
THISMONTHBILLAMT,
OUTSTANDINGAMT,
PENALTYAMT,
DRACCTNO,
CRACCTNO,debit_30,debit_30_60,debit_60 from bill a,delivery b where a.billkey=b.bill_key and BILLKEY not in (select BILLKEY from payment)
    """

    params = {}

    # Add search filter if search_query is provided
    if search_query:
        query += " AND (a.CUSTOMERKEY LIKE :search OR a.BILLKEY LIKE :search)"
        params['search'] = f'%{search_query}%'

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += "AND  a.CUSTOMERBRANCH = :branch"
        params['branch'] = selected_branch

    # Add date range filter if both start_date and end_date are provided
    # if start_date and end_date:
    #     query += """
    #     AND TO_DATE(SUBSTR(a.PAYMENTDATE, 1, 10), 'YYYY-MM-DD') 
    #     BETWEEN TO_DATE(:start_date, 'YYYY-MM-DD') 
    #     AND TO_DATE(:end_date, 'YYYY-MM-DD')
    #     """
    #     params['start_date'] = start_date  # Pass 'YYYY-MM-DD' formatted string
    #     params['end_date'] = end_date      # Pass 'YYYY-MM-DD' formatted string

    # Finalize query order

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    print(query)
    filtered_records = cursor.fetchall()  # Now this contains only filtered results
    # print(filtered_records)

    # Pagination logic
    total = len(filtered_records)  # Total number of filtered records
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    payments_paginated = filtered_records[start:end]

    # Export functionality: pass the filtered data (filtered_records) to export functions
    if export_format == 'csv':
        return export_unsettled_csv(filtered_records)  # Export filtered data
    elif export_format == 'pdf':
        return export_unsettled_pdf(filtered_records)  # Export filtered data
    elif export_format == 'excel':
        return export_unsettled_excel(filtered_records)  # Export filtered data

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches()
    branches = get_branches()

    # Render the template and pass paginated payments data
    return render_template(
        'list_unsettled_bills.html',
        delivery=payments_paginated,
        search_query=search_query,
        branches=branches,
        selected_branch=selected_branch,
        # start_date=start_date,
        # end_date=end_date,
        page=page,
        pages=pages
    )



@app.route('/call_center_unsettled', methods=['GET', 'POST'])
@login_required
def call_center_unsettled():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 300  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
     Select BILLKEY,
a.CUSTOMERKEY,
SUBSTR(CUSTOMERNAME,1,30) as CUSTOMERNAME,
CUSTOMERTIN,
CUSTOMERBRANCH,
REASON,
CURRREAD,
PREVREAD,
CONS,
TOTALBILLAMOUNT,
THISMONTHBILLAMT,
OUTSTANDINGAMT,
PENALTYAMT,
DRACCTNO,
CRACCTNO,PHONENUMBER,route_key,charge_group,CONTRACT_NUMBER,METER_KEY 
from bill a,cust_phone b,delivery c where a.CUSTOMERKEY=b.CUSTOMERKEY and a.billkey=c.bill_key 
and BILLKEY not in (select BILLKEY from payment)
    """

    params = {}

    # Add search filter if search_query is provided
    if search_query:
        query += " AND (a.CUSTOMERKEY LIKE :search OR a.BILLKEY LIKE :search)"
        params['search'] = f'%{search_query}%'

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += "AND  a.CUSTOMERBRANCH = :branch"
        params['branch'] = selected_branch


    # Finalize query order

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()  # Now this contains only filtered results
    # print(filtered_records)

    # Pagination logic
    total = len(filtered_records)  # Total number of filtered records
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    payments_paginated = filtered_records[start:end]

    # Export functionality: pass the filtered data (filtered_records) to export functions
    if export_format == 'csv':
        return export_callcenter_csv(filtered_records)  # Export filtered data
    elif export_format == 'pdf':
        return export_callcenter_pdf(filtered_records)  # Export filtered data
    elif export_format == 'excel':
        return export_callcenter_excel(filtered_records)  # Export filtered data

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches()
    branches = get_branches()

    # Render the template and pass paginated payments data
    return render_template(
        'call_center_unsettled.html',
        call_center_unsettled=payments_paginated,
        search_query=search_query,
        branches=branches,
        selected_branch=selected_branch,
        # start_date=start_date,
        # end_date=end_date,
        page=page,
        pages=pages
    )


@app.route('/bill_table_ubs_export', methods=['GET', 'POST'])
@login_required
def bill_table_ubs_export():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    selected_period = request.args.get('period', 'All')  # Get the selected period from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 10  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
        SELECT NAME,
               CUST_KEY,
               INST_KEY,
               CONTRACT_NUMBER,
               CHARGE_GROUP,
               ROUTE_KEY,
               READING_DATE,
               BILL_KEY,
               WALK_ORDER,
               BRANCH,
               PERIOD,
               ADDRESS,
               WATER_CONS,
               MAINTAINANCE,
               SEWERAGE,
               SANITATION,
               METER_RENT,
               METER_KEY,
               OLD_METER_CONS,
               LAST_RDG_OLD_MTR,
               PREV_RDG,
               CURR_RDG,
               CURR_CONS,
               TOT_CONS,
               CATEGORY_TYPE,
               BLOCK1_CNS,
               BLOCK2_CNS,
               BLOCK3_CNS,
               BLOCK4_CNS,
               BLOCK5_CNS,
               BLOCK6_CNS,
               BLOCK7_CNS,
               BLOCK1_TRF,
               BLOCK2_TRF,
               BLOCK3_TRF,
               BLOCK4_TRF,
               BLOCK5_TRF,
               BLOCK6_TRF,
               BLOCK7_TRF,
               BLOCK1_AMNT,
               BLOCK2_AMNT,
               BLOCK3_AMNT,
               BLOCK4_AMNT,
               BLOCK5_AMNT,
               BLOCK6_AMNT,
               BLOCK7_AMNT,
               METER_DIAMETER,
               BILL_AMOUNT,
               DEBIT_30,
               DEBIT_30_60,
               DEBIT_60,
               TOT_AMNT,
               CONS_PERIOD,
               DUE_DATE,
               IS_FETCHED,
               SEND_COUNT,
               BILL_ID,
               INST_ID,
               CUST_ID,
               BILL_DATE,
               BILL_FILE_TRAN_ID
        FROM delivery
        WHERE 1=1
    """

    params = {}

    # Add search filter if search_query is provided
    if search_query:
        query += " AND (CUST_KEY LIKE :search OR NAME LIKE :search OR BILL_KEY LIKE :search)"
        params['search'] = f'%{search_query}%'

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND BRANCH = :branch"
        params['branch'] = selected_branch

    # Add period filter if a period is selected
    if selected_period != 'All':
        query += " AND PERIOD = :period"
        params['period'] = selected_period

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    paginated_records = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_ubs_csv(filtered_records)  # Export all filtered data
    elif export_format == 'pdf':
        return export_ubs_pdf(filtered_records)  # Export all filtered data
    elif export_format == 'excel':
        return export_ubs_excel(filtered_records)  # Export all filtered data
     # branches = get_branches_ubs()
    # periods = get_periods()
    cursor.execute("SELECT DISTINCT BRANCH FROM delivery")
    branches = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT PERIOD FROM delivery ORDER BY PERIOD DESC")
    periods = [row[0] for row in cursor.fetchall()]

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches() and periods with get_periods()
   

    # Render the template and pass paginated data and filter options
    return render_template(
        'bill_table_ubs.html',
        records=paginated_records,
        search_query=search_query,
        branches=branches,
        periods=periods,
        selected_branch=selected_branch,
        selected_period=selected_period,
        page=page,
        pages=pages
    )


def get_periods():
    # Establish database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query to get distinct periods from the bill_table_ubs
    cursor.execute("SELECT DISTINCT PERIOD FROM bill_table_ubs ORDER BY PERIOD DESC")
    
    # Fetch all the periods
    periods = cursor.fetchall()

    # Close connection
    cursor.close()
    conn.close()

    # Return the list of periods
    return [row[0] for row in periods]  # Assuming the first column contains the PERIOD
@app.route('/list_paid_bills', methods=['GET', 'POST'])
@login_required
def list_paid_bills():
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
     SELECT PAYMENTKEY,a.BILLKEY,a.CUSTOMERKEY,a.AMOUNT,BANKTXNREF,PAYMENTCHANNEL,
    PAYMENTDATE,REQUESTID,CHANNEL,CUSTOMERNAME,CUSTOMERTIN,
    CUSTOMERBRANCH,REASON,CURRREAD,PREVREAD,CONS,TOTALBILLAMOUNT,THISMONTHBILLAMT,
    OUTSTANDINGAMT,PENALTYAMT,DRACCTNO,CRACCTNO,PAYMENTCOMPLETEDAT
    FROM payment a, bill b 
    WHERE a.BILLKEY = b.BILLKEY
    """

    params = {}

    # Add search filter if search_query is provided
    if search_query:
        query += " AND (a.CUSTOMERKEY LIKE :search OR a.BILLKEY LIKE :search)"
        params['search'] = f'%{search_query}%'

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND b.CUSTOMERBRANCH = :branch"
        params['branch'] = selected_branch

    if start_date and end_date:
        try:
            # Convert from HTML datetime-local format (with 'T' and possibly missing seconds)
            if 'T' in start_date:
                start_date = start_date.replace('T', ' ') + ':00'
            if 'T' in end_date:
                end_date = end_date.replace('T', ' ') + ':00'

            dt_format = '%Y-%m-%d %H:%M:%S'
            start_date_obj = datetime.strptime(start_date, dt_format)
            end_date_obj = datetime.strptime(end_date, dt_format)

            query += """
            AND a.PAYMENTCOMPLETEDAT 
            BETWEEN TO_DATE(:start_date, 'YYYY-MM-DD HH24:MI:SS') 
            AND TO_DATE(:end_date, 'YYYY-MM-DD HH24:MI:SS')
            """
            params['start_date'] = start_date_obj.strftime(dt_format)
            params['end_date'] = end_date_obj.strftime(dt_format)

        except ValueError:
            return "Invalid datetime format. Please use YYYY-MM-DDTHH:MM from input."


    # Finalize query order
    query += " ORDER BY a.BILLKEY"

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
        return export_paid_pdf(filtered_records)  # Export filtered data
    elif export_format == 'excel':
        return export_paid_excel(filtered_records)  # Export filtered data

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches()
    branches = get_branches()

    # Render the template and pass paginated payments data
    return render_template(
        'list_paid_bills.html',
        payments=payments_paginated,
        search_query=search_query,
        branches=branches,
        selected_branch=selected_branch,
        start_date=start_date,
        end_date=end_date,
        page=page,
        pages=pages
    )

def get_members():
    """
    Retrieves the list of distinct branches from the BILL table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT DISTINCT SECTION_NAME FROM MEMBER_REGISTRATION ORDER BY SECTION_NAME"
    cursor.execute(query)
    branches = cursor.fetchall()
    cursor.close()
    conn.close()
    return [branch[0] for branch in branches]  # Extract the branch names from the tuple

# def get_members():
#     # Establish database connection
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     # Query to get distinct periods from the bill_table_ubs
#     cursor.execute("SELECT DISTINCT SECTION_NAME FROM MEMBER_REGISTRATION ORDER BY SECTION_NAME DESC")
    
#     # Fetch all the periods
#     periods = cursor.fetchall()

#     # Close connection
#     cursor.close()
#     conn.close()


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
        query += " AND (a.FULL_NAME LIKE :search OR a.PHONE LIKE :search)"
        params['search'] = f'%{search_query}%'

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND a.SECTION_NAME = :branch"
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
            BETWEEN TO_DATE(:start_date, 'YYYY-MM-DD ') 
            AND TO_DATE(:end_date, 'YYYY-MM-DD ')
            """
            params['start_date'] = start_date_obj.strftime(dt_format)
            params['end_date'] = end_date_obj.strftime(dt_format)

        except ValueError:
            return "Invalid datetime format. Please use YYYY-MM-DDTHH:MM from input."


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





@app.route('/delivery_route_export', methods=['GET', 'POST'])
@login_required
def delivery_route_export():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    selected_period = request.args.get('period', 'All')  # Get the selected period from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 10  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection_billing()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
        SELECT PERIOD,
BRANCH,
ROUTE_KEY,
TO_CHAR(NUMBER_OF_BILL,'FM999,999,999'),
TO_CHAR(WATER_CONS,'FM999,999,999.99'),
TO_CHAR(METER_RENT,'FM999,999,999.99'),
TO_CHAR(SANITATION,'FM999,999,999.99'),
TO_CHAR(SEWERAGE,'FM999,999,999.99'),
TO_CHAR(VAT_AMOUNT,'FM999,999,999.99'),
TO_CHAR(BILL_AMOUNT,'FM999,999,999.99'),
TO_CHAR(DEBIT_30,'FM999,999,999.99'),
TO_CHAR(DEBIT_30_60,'FM999,999,999.99'),
TO_CHAR(DEBIT_60,'FM999,999,999.99'),
TO_CHAR(TOT_AMNT,'FM999,999,999.99')
        FROM dasbord_delivery_with_cg
        WHERE 1=1
    """

    params = {}

    # Add search filter if search_query is provided

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND BRANCH = :branch"
        params['branch'] = selected_branch

    # Add period filter if a period is selected
    if selected_period != 'All':
        query += " AND PERIOD = :period"
        params['period'] = selected_period
    query += " ORDER BY PERIOD,branch,ROUTE_KEY"

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    paginated_records = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_delivery_route_csv(filtered_records)  # Export all filtered data
    elif export_format == 'pdf':
        return export_delivery_route_pdf(filtered_records)  # Export all filtered data
    elif export_format == 'excel':
        return export_delivery_route_excel(filtered_records)  # Export all filtered data
     # branches = get_branches_ubs()
    # periods = get_periods()
    cursor.execute("SELECT DISTINCT BRANCH FROM dasbord_delivery_with_cg")
    branches = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT PERIOD FROM dasbord_delivery_with_cg ORDER BY PERIOD DESC")
    periods = [row[0] for row in cursor.fetchall()]

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches() and periods with get_periods()
   

    # Render the template and pass paginated data and filter options
    return render_template(
        'delivery_by_route_key.html',
        records=paginated_records,
        search_query=search_query,
        branches=branches,
        periods=periods,
        selected_branch=selected_branch,
        selected_period=selected_period,
        page=page,
        pages=pages
    )

@app.route('/settled_route_export', methods=['GET', 'POST'])
@login_required
def settled_route_export():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    selected_period = request.args.get('period', 'All')  # Get the selected period from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 10  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection_billing()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
        SELECT PERIOD,
BRANCH,
ROUTE_KEY,
NUMBER_OF_BILL,
WATER_CONS,
METER_RENT,
SANITATION,
SEWERAGE,
VAT_AMOUNT,
BILL_AMOUNT,
DEBIT_30,
DEBIT_30_60,
DEBIT_60,
TOT_AMNT
        FROM dasbord_settled_with_cg
        WHERE 1=1
    """

    params = {}

    # Add search filter if search_query is provided

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND BRANCH = :branch"
        params['branch'] = selected_branch

    # Add period filter if a period is selected
    if selected_period != 'All':
        query += " AND PERIOD = :period"
        params['period'] = selected_period
    query += " ORDER BY PERIOD,branch,ROUTE_KEY"

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    paginated_records = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_settled_route_csv(filtered_records)  # Export all filtered data
    elif export_format == 'pdf':
        return export_settled_route_pdf(filtered_records)  # Export all filtered data
    elif export_format == 'excel':
        return export_settled_route_excel(filtered_records)  # Export all filtered data
     # branches = get_branches_ubs()
    # periods = get_periods()
    cursor.execute("SELECT DISTINCT BRANCH FROM dasbord_settled_with_cg")
    branches = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT PERIOD FROM dasbord_settled_with_cg ORDER BY PERIOD DESC")
    periods = [row[0] for row in cursor.fetchall()]

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches() and periods with get_periods()
   

    # Render the template and pass paginated data and filter options
    return render_template(
        'settled_by_route_key.html',
        records=paginated_records,
        search_query=search_query,
        branches=branches,
        periods=periods,
        selected_branch=selected_branch,
        selected_period=selected_period,
        page=page,
        pages=pages
    )

@app.route('/unsettled_route_export', methods=['GET', 'POST'])
@login_required
def unsettled_route_export():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    selected_period = request.args.get('period', 'All')  # Get the selected period from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 10  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection_billing()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
        SELECT PERIOD,
BRANCH,
ROUTE_KEY,
NUMBER_OF_BILL,
WATER_CONS,
METER_RENT,
SANITATION,
SEWERAGE,
VAT_AMOUNT,
BILL_AMOUNT,
DEBIT_30,
DEBIT_30_60,
DEBIT_60,
TOT_AMNT
        FROM dasbord_unsettled_with_cg
        WHERE 1=1
    """

    params = {}

    # Add search filter if search_query is provided

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND BRANCH = :branch"
        params['branch'] = selected_branch

    # Add period filter if a period is selected
    if selected_period != 'All':
        query += " AND PERIOD = :period"
        params['period'] = selected_period
    query += " ORDER BY PERIOD,branch,ROUTE_KEY"

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    paginated_records = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_unsettled_route_csv(filtered_records)  # Export all filtered data
    elif export_format == 'pdf':
        return export_unsettled_route_pdf(filtered_records)  # Export all filtered data
    elif export_format == 'excel':
        return export_unsettled_route_excel(filtered_records)  # Export all filtered data
     # branches = get_branches_ubs()
    # periods = get_periods()
    cursor.execute("SELECT DISTINCT BRANCH FROM dasbord_unsettled_with_cg")
    branches = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT PERIOD FROM dasbord_unsettled_with_cg ORDER BY PERIOD DESC")
    periods = [row[0] for row in cursor.fetchall()]

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches() and periods with get_periods()
   

    # Render the template and pass paginated data and filter options
    return render_template(
        'unsettled_by_route_key.html',
        records=paginated_records,
        search_query=search_query,
        branches=branches,
        periods=periods,
        selected_branch=selected_branch,
        selected_period=selected_period,
        page=page,
        pages=pages
    )


@app.route('/settled_cg_export', methods=['GET', 'POST'])
@login_required
def settled_cg_export():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    selected_period = request.args.get('period', 'All')  # Get the selected period from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 10  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection_billing()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
        SELECT PERIOD,
BRANCH,
Charge_group,
NUMBER_OF_BILL,
WATER_CONS,
METER_RENT,
SANITATION,
SEWERAGE,
VAT_AMOUNT,
BILL_AMOUNT,
DEBIT_30,
DEBIT_30_60,
DEBIT_60,
TOT_AMNT
        FROM dasbord_settled_with_cgg
        WHERE 1=1
    """

    params = {}

    # Add search filter if search_query is provided

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND BRANCH = :branch"
        params['branch'] = selected_branch

    # Add period filter if a period is selected
    if selected_period != 'All':
        query += " AND PERIOD = :period"
        params['period'] = selected_period
    query += " ORDER BY PERIOD,branch,Charge_group"

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    paginated_records = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_settled_cg_csv(filtered_records)  # Export all filtered data
    elif export_format == 'pdf':
        return export_settled_cg_pdf(filtered_records)  # Export all filtered data
    elif export_format == 'excel':
        return export_settled_cg_excel(filtered_records)  # Export all filtered data
     # branches = get_branches_ubs()
    # periods = get_periods()
    cursor.execute("SELECT DISTINCT BRANCH FROM dasbord_settled_with_cgg")
    branches = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT PERIOD FROM dasbord_settled_with_cgg ORDER BY PERIOD DESC")
    periods = [row[0] for row in cursor.fetchall()]

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches() and periods with get_periods()
   

    # Render the template and pass paginated data and filter options
    return render_template(
        'settled_by_charge_group.html',
        records=paginated_records,
        search_query=search_query,
        branches=branches,
        periods=periods,
        selected_branch=selected_branch,
        selected_period=selected_period,
        page=page,
        pages=pages
    )

@app.route('/unsettled_cg_export', methods=['GET', 'POST'])
@login_required
def unsettled_cg_export():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    selected_period = request.args.get('period', 'All')  # Get the selected period from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 10  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection_billing()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
        SELECT PERIOD,
BRANCH,
Charge_group,
NUMBER_OF_BILL,
WATER_CONS,
METER_RENT,
SANITATION,
SEWERAGE,
VAT_AMOUNT,
BILL_AMOUNT,
DEBIT_30,
DEBIT_30_60,
DEBIT_60,
TOT_AMNT
        FROM dasbord_unsettled_with_cgg
        WHERE 1=1
    """

    params = {}

    # Add search filter if search_query is provided

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND BRANCH = :branch"
        params['branch'] = selected_branch

    # Add period filter if a period is selected
    if selected_period != 'All':
        query += " AND PERIOD = :period"
        params['period'] = selected_period
    query += " ORDER BY PERIOD,branch,Charge_group"

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    paginated_records = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_unsettled_cg_csv(filtered_records)  # Export all filtered data
    elif export_format == 'pdf':
        return export_unsettled_cg_pdf(filtered_records)  # Export all filtered data
    elif export_format == 'excel':
        return export_unsettled_cg_excel(filtered_records)  # Export all filtered data
     # branches = get_branches_ubs()
    # periods = get_periods()
    cursor.execute("SELECT DISTINCT BRANCH FROM dasbord_unsettled_with_cgg")
    branches = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT PERIOD FROM dasbord_unsettled_with_cgg ORDER BY PERIOD DESC")
    periods = [row[0] for row in cursor.fetchall()]

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches() and periods with get_periods()
   

    # Render the template and pass paginated data and filter options
    return render_template(
        'unsettled_by_charge_group.html',
        records=paginated_records,
        search_query=search_query,
        branches=branches,
        periods=periods,
        selected_branch=selected_branch,
        selected_period=selected_period,
        page=page,
        pages=pages
    )

@app.route('/delivery_cg_export', methods=['GET', 'POST'])
@login_required
def delivery_cg_export():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    selected_period = request.args.get('period', 'All')  # Get the selected period from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 10  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection_billing()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
        SELECT PERIOD,
BRANCH,
Charge_group,
NUMBER_OF_BILL,
WATER_CONS,
METER_RENT,
SANITATION,
SEWERAGE,
VAT_AMOUNT,
BILL_AMOUNT,
DEBIT_30,
DEBIT_30_60,
DEBIT_60,
TOT_AMNT
        FROM dasbord_delivery_with_cgg
        WHERE 1=1
    """

    params = {}

    # Add search filter if search_query is provided

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND BRANCH = :branch"
        params['branch'] = selected_branch

    # Add period filter if a period is selected
    if selected_period != 'All':
        query += " AND PERIOD = :period"
        params['period'] = selected_period
    query += " ORDER BY PERIOD,branch,Charge_group"

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    paginated_records = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_unsettled_cg_csv(filtered_records)  # Export all filtered data
    elif export_format == 'pdf':
        return export_unsettled_cg_pdf(filtered_records)  # Export all filtered data
    elif export_format == 'excel':
        return export_unsettled_cg_excel(filtered_records)  # Export all filtered data
     # branches = get_branches_ubs()
    # periods = get_periods()
    cursor.execute("SELECT DISTINCT BRANCH FROM dasbord_delivery_with_cgg")
    branches = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT PERIOD FROM dasbord_delivery_with_cgg ORDER BY PERIOD DESC")
    periods = [row[0] for row in cursor.fetchall()]

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches() and periods with get_periods()
   

    # Render the template and pass paginated data and filter options
    return render_template(
        'delivery_by_charge_group.html',
        records=paginated_records,
        search_query=search_query,
        branches=branches,
        periods=periods,
        selected_branch=selected_branch,
        selected_period=selected_period,
        page=page,
        pages=pages
    )

@app.route('/gl_detail_export', methods=['GET', 'POST'])
@login_required
def gl_detail_export():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    selected_period = request.args.get('period', 'All')  # Get the selected period from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 10  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection_billing()
    cursor = conn.cursor()

    # Base query for filtering
    query = """

             
    SELECT COUNT,BRANCH,GL_CODE,TOTAL_AMOUNT,VAT_AMOUNT,WITH_OUT_VAT,PERIOD 
    FROM dasbord_gl_detalis WHERE 1=1
        
    """

    params = {}

    # Add search filter if search_query is provided

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND BRANCH = :branch"
        params['branch'] = selected_branch

    # Add period filter if a period is selected
    if selected_period != 'All':
        query += " AND PERIOD = :period"
        params['period'] = selected_period
    query += " ORDER BY PERIOD,branch"

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    paginated_records = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_gl_detail_csv(filtered_records)  # Export all filtered data
    elif export_format == 'pdf':
        return export_gl_detail_pdf(filtered_records)  # Export all filtered data
    elif export_format == 'excel':
        return export_gl_detail_excel(filtered_records)  # Export all filtered data
     # branches = get_branches_ubs()
    # periods = get_periods()
    cursor.execute("SELECT DISTINCT BRANCH FROM dasbord_gl_detalis")
    branches = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT PERIOD FROM dasbord_gl_detalis ORDER BY PERIOD DESC")
    periods = [row[0] for row in cursor.fetchall()]

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches() and periods with get_periods()
   

    # Render the template and pass paginated data and filter options
    return render_template(
        'gl_detail.html',
        records=paginated_records,
        search_query=search_query,
        branches=branches,
        periods=periods,
        selected_branch=selected_branch,
        selected_period=selected_period,
        page=page,
        pages=pages
    )



@app.route('/bill_current_corr_export', methods=['GET', 'POST'])
@login_required
def bill_current_corr_export():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    selected_period = request.args.get('period', 'All')  # Get the selected period from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 10  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query for filtering
    query = """

             
    select a.CORRECTION_ID,a.billkey,CUSTOMERKEY,CUSTOMERNAME,CUSTOMERBRANCH,REASON,TOTALBILLAMOUNT,a.ACTION,a.PERFORMED_BY,
    a.PERFORMED_AT from payment_corrections a,bill b where a.billkey=b.billkey 

        
    """

    params = {}

    # Add search filter if search_query is provided

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND CUSTOMERBRANCH = :branch"
        params['branch'] = selected_branch

    # Add period filter if a period is selected
    if selected_period != 'All':
        query += " AND REASON = :period"
        params['period'] = selected_period
    query += " ORDER BY REASON,CUSTOMERBRANCH"

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    paginated_records = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_current_corr_csv(filtered_records)  # Export all filtered data
    elif export_format == 'pdf':
        return export_current_corr_pdf(filtered_records)  # Export all filtered data
    elif export_format == 'excel':
        return export_current_corr_excel(filtered_records)  # Export all filtered data
     # branches = get_branches_ubs()
    # periods = get_periods()
    cursor.execute("SELECT DISTINCT CUSTOMERBRANCH FROM bill")
    branches = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT REASON FROM bill ORDER BY REASON DESC")
    periods = [row[0] for row in cursor.fetchall()]

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches() and periods with get_periods()
   

    # Render the template and pass paginated data and filter options
    return render_template(
        'current_bill_corr.html',
        records=paginated_records,
        search_query=search_query,
        branches=branches,
        periods=periods,
        selected_branch=selected_branch,
        selected_period=selected_period,
        page=page,
        pages=pages
    )


@app.route('/bill_past_corr_export', methods=['GET', 'POST'])
@login_required
def bill_past_corr_export():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    selected_period = request.args.get('period', 'All')  # Get the selected period from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 10  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query for filtering
    query = """

             
    select a.CORRECTION_ID,a.billkey,CUSTOMERKEY,CUSTOMERNAME,CUSTOMERBRANCH,REASON,TOTALBILLAMOUNT,a.ACTION,a.PERFORMED_BY,
    a.PERFORMED_AT from payment_corrections a,bill_old b where a.billkey=b.billkey 

        
    """

    params = {}

    # Add search filter if search_query is provided

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " AND CUSTOMERBRANCH = :branch"
        params['branch'] = selected_branch

    # Add period filter if a period is selected
    if selected_period != 'All':
        query += " AND REASON = :period"
        params['period'] = selected_period
    query += " ORDER BY REASON,CUSTOMERBRANCH"

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    paginated_records = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_past_corr_csv(filtered_records)  # Export all filtered data
    elif export_format == 'pdf':
        return export_past_corr_pdf(filtered_records)  # Export all filtered data
    elif export_format == 'excel':
        return export_past_corr_excel(filtered_records)  # Export all filtered data
     # branches = get_branches_ubs()
    # periods = get_periods()
    cursor.execute("SELECT DISTINCT CUSTOMERBRANCH FROM bill_old")
    branches = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT REASON FROM bill_old ORDER BY REASON DESC")
    periods = [row[0] for row in cursor.fetchall()]

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches() and periods with get_periods()
   

    # Render the template and pass paginated data and filter options
    return render_template(
        'past_bill_corr.html',
        records=paginated_records,
        search_query=search_query,
        branches=branches,
        periods=periods,
        selected_branch=selected_branch,
        selected_period=selected_period,
        page=page,
        pages=pages
    )


@app.route('/xyz_export', methods=['GET', 'POST'])
@login_required
def xyz_export():
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')  # Get the selected branch from query parameters
    # selected_period = request.args.get('period', 'All')  # Get the selected period from query parameters
    export_format = request.args.get('format', None)  # Get export format from query parameters
    page = request.args.get('page', 1, type=int)  # Get the current page number, default to 1
    per_page = 10  # Number of items per page

    if request.method == 'POST':
        search_query = request.form.get('search', '')

    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query for filtering
    query = """
    select CUSTOMERKEY,METERKEY,CUSTOMERNAME,CUSTOMERADDRESS,CUSTOMERBRANCH,LATTITUDE,LONGITUDE,ALTITUDE,ROUTEID from xyz
    """

    params = {}

    # Add search filter if search_query is provided

    # Add branch filter if a branch is selected
    if selected_branch != 'All':
        query += " Where CUSTOMERBRANCH = :branch"
        params['branch'] = selected_branch

    query += " ORDER BY CUSTOMERBRANCH"

    # Execute the query to fetch filtered records for export and pagination
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)  # Total number of pages
    start = (page - 1) * per_page  # Start index for the current page
    end = start + per_page  # End index for the current page

    # Fetch only the rows for the current page (pagination)
    paginated_records = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_xyz_csv(filtered_records)  # Export all filtered data
    elif export_format == 'pdf':
        return export_xyz_pdf(filtered_records)  # Export all filtered data
    elif export_format == 'excel':
        return export_xyz_excel(filtered_records)  # Export all filtered data
     # branches = get_branches_ubs()
    # periods = get_periods()
    cursor.execute("SELECT DISTINCT CUSTOMERBRANCH FROM xyz")
    branches = [row[0] for row in cursor.fetchall()]

    # cursor.execute("SELECT DISTINCT REASON FROM bill_old ORDER BY REASON DESC")
    # periods = [row[0] for row in cursor.fetchall()]

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches for the filter dropdown using get_branches() and periods with get_periods()
   

    # Render the template and pass paginated data and filter options
    return render_template(
        'xyz.html',
        records=paginated_records,
        search_query=search_query,
        branches=branches,
        # periods=periods,
        selected_branch=selected_branch,
        # selected_period=selected_period,
        page=page,
        pages=pages
    )



def export_xyz_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
        'CUSTOMERKEY','METERKEY','CUSTOMERNAME','CUSTOMERADDRESS','CUSTOMERBRANCH','LATTITUDE','LONGITUDE','ALTITUDE','ROUTEID'

    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='XYZ Report.csv')


def export_xyz_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=10,
        leftMargin=10,
        topMargin=40,
        bottomMargin=70  # Leave space for signature and page number
    )

    elements = []

    # Try to add logo at the top
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>XYZ Report </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
       'CUSTOMERKEY','METERKEY','CUSTOMERNAME','CUSTOMERADDRESS','CUSTOMERBRANCH','LATTITUDE','LONGITUDE','ALTITUDE','ROUTEID''CUSTOMERKEY','METERKEY','CUSTOMERNAME','CUSTOMERADDRESS','CUSTOMERBRANCH','LATTITUDE','LONGITUDE','ALTITUDE','ROUTEID'

    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = [Paragraph(str(item) if item else '', wrap_style) for item in row]
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)

    # Footer callback
    def add_footer(canvas, doc):
        canvas.saveState()

        # Add page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(415, 15, f"Page {page_num}")

        # Optional: Add stamp and signature (images must exist)
        try:
            canvas.drawImage('static/img/teter2.png', 30, 5, width=1*inch, height=1*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        try:
            canvas.drawImage('static/img/sign1.png', 650, 5, width=1.2*inch, height=0.5*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='XYZ Report.pdf')

def export_xyz_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "XYZ Report"

    # Define headers
    headers = ['CUSTOMERKEY','METERKEY','CUSTOMERNAME','CUSTOMERADDRESS','CUSTOMERBRANCH','LATTITUDE','LONGITUDE','ALTITUDE','ROUTEID'
]
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='XYZ Report.xlsx')






def export_past_corr_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
        'CORRECTION_ID','billkey','CUSTOMERKEY','CUSTOMERNAME','CUSTOMERBRANCH','REASON','TOTALBILLAMOUNT','ACTION','PERFORMED_BY',
    'PERFORMED_AT'

    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Past Month Bill Correction Report.csv')


def export_past_corr_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=10,
        leftMargin=10,
        topMargin=40,
        bottomMargin=70  # Leave space for signature and page number
    )

    elements = []

    # Try to add logo at the top
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Past Month Bill Correction and Dishonnerd </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'CORRECTION_ID','billkey','CUSTOMERKEY','CUSTOMERNAME','CUSTOMERBRANCH','REASON','TOTALBILLAMOUNT','ACTION','PERFORMED_BY',
    'PERFORMED_AT'

    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = [Paragraph(str(item) if item else '', wrap_style) for item in row]
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)

    # Footer callback
    def add_footer(canvas, doc):
        canvas.saveState()

        # Add page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(415, 15, f"Page {page_num}")

        # Optional: Add stamp and signature (images must exist)
        try:
            canvas.drawImage('static/img/teter2.png', 30, 5, width=1*inch, height=1*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        try:
            canvas.drawImage('static/img/sign1.png', 650, 5, width=1.2*inch, height=0.5*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Past Month Correction and Dishonnerd.pdf')

def export_past_corr_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "GL Details Report"

    # Define headers
    headers = ['CORRECTION_ID','billkey','CUSTOMERKEY','CUSTOMERNAME','CUSTOMERBRANCH','REASON','TOTALBILLAMOUNT','ACTION','PERFORMED_BY',
    'PERFORMED_AT'
]
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Past Month Bill Corrections.xlsx')






def export_current_corr_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
        'CORRECTION_ID','billkey','CUSTOMERKEY','CUSTOMERNAME','CUSTOMERBRANCH','REASON','TOTALBILLAMOUNT','ACTION','PERFORMED_BY',
    'PERFORMED_AT'

    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Current Month Bill Correction Report.csv')


def export_current_corr_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=10,
        leftMargin=10,
        topMargin=40,
        bottomMargin=70  # Leave space for signature and page number
    )

    elements = []

    # Try to add logo at the top
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Current Month Bill Correction and Dishonnerd </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'CORRECTION_ID','billkey','CUSTOMERKEY','CUSTOMERNAME','CUSTOMERBRANCH','REASON','TOTALBILLAMOUNT','ACTION','PERFORMED_BY',
    'PERFORMED_AT'

    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = [Paragraph(str(item) if item else '', wrap_style) for item in row]
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)

    # Footer callback
    def add_footer(canvas, doc):
        canvas.saveState()

        # Add page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(415, 15, f"Page {page_num}")

        # Optional: Add stamp and signature (images must exist)
        try:
            canvas.drawImage('static/img/teter2.png', 30, 5, width=1*inch, height=1*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        try:
            canvas.drawImage('static/img/sign1.png', 650, 5, width=1.2*inch, height=0.5*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Current Month Correction and Dishonnerd.pdf')

def export_current_corr_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "GL Details Report"

    # Define headers
    headers = ['CORRECTION_ID','billkey','CUSTOMERKEY','CUSTOMERNAME','CUSTOMERBRANCH','REASON','TOTALBILLAMOUNT','ACTION','PERFORMED_BY',
    'PERFORMED_AT'
]
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Current Month Bill Corrections.xlsx')



def export_gl_detail_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
        'COUNT','BRANCH','GL_CODE','TOTAL_AMOUNT','VAT_AMOUNT','WITH_OUT_VAT','PERIOD'

    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='GL Details Report.csv')


def export_gl_detail_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=10,
        leftMargin=10,
        topMargin=40,
        bottomMargin=70  # Leave space for signature and page number
    )

    elements = []

    # Try to add logo at the top
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>GL Details Reports </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'COUNT','BRANCH','GL_CODE','TOTAL_AMOUNT','VAT_AMOUNT','WITH_OUT_VAT','PERIOD'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = [Paragraph(str(item) if item else '', wrap_style) for item in row]
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)

    # Footer callback
    def add_footer(canvas, doc):
        canvas.saveState()

        # Add page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(415, 15, f"Page {page_num}")

        # Optional: Add stamp and signature (images must exist)
        try:
            canvas.drawImage('static/img/teter2.png', 30, 5, width=1*inch, height=1*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        try:
            canvas.drawImage('static/img/sign1.png', 650, 5, width=1.2*inch, height=0.5*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='GL Details Reports.pdf')

def export_gl_detail_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "GL Details Report"

    # Define headers
    headers = ['COUNT','BRANCH','GL_CODE','TOTAL_AMOUNT','VAT_AMOUNT','WITH_OUT_VAT','PERIOD']
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='GL details Report.xlsx')




def export_delivery_cg_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'PERIOD',
'BRANCH',
'Charge Group',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Delivery by Charge Group.csv')


def export_delivery_cg_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=10,
        leftMargin=10,
        topMargin=40,
        bottomMargin=70  # Leave space for signature and page number
    )

    elements = []

    # Try to add logo at the top
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Delivery by Charge Group This Month </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'PERIOD', 'BRANCH', 'Charge Group', 'NUMBER_OF_BILL', 'WATER_CONS',
        'METER_RENT', 'SANITATION', 'SEWERAGE', 'VAT_AMOUNT', 'BILL_AMOUNT',
        'DEBIT_30', 'DEBIT_30_60', 'DEBIT_60', 'TOT_AMNT'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = [Paragraph(str(item) if item else '', wrap_style) for item in row]
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)

    # Footer callback
    def add_footer(canvas, doc):
        canvas.saveState()

        # Add page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(415, 15, f"Page {page_num}")

        # Optional: Add stamp and signature (images must exist)
        try:
            canvas.drawImage('static/img/teter2.png', 30, 5, width=1*inch, height=1*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        try:
            canvas.drawImage('static/img/sign1.png', 650, 5, width=1.2*inch, height=0.5*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Delivery by Charge Group.pdf')

def export_delivery_cg_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Delivery by Charge Group"

    # Define headers
    headers = ['PERIOD',
'BRANCH',
'Charge Group',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
]
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Delivery by charge group.xlsx')

def export_settled_cg_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'PERIOD',
'BRANCH',
'Charge Group',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Delivery by Charge Group.csv')


def export_settled_cg_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=10,
        leftMargin=10,
        topMargin=40,
        bottomMargin=70  # Leave space for signature and page number
    )

    elements = []

    # Try to add logo at the top
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Delivery by Charge Group This Month </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'PERIOD', 'BRANCH', 'Charge Group', 'NUMBER_OF_BILL', 'WATER_CONS',
        'METER_RENT', 'SANITATION', 'SEWERAGE', 'VAT_AMOUNT', 'BILL_AMOUNT',
        'DEBIT_30', 'DEBIT_30_60', 'DEBIT_60', 'TOT_AMNT'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = [Paragraph(str(item) if item else '', wrap_style) for item in row]
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)

    # Footer callback
    def add_footer(canvas, doc):
        canvas.saveState()

        # Add page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(415, 15, f"Page {page_num}")

        # Optional: Add stamp and signature (images must exist)
        try:
            canvas.drawImage('static/img/teter2.png', 30, 5, width=1*inch, height=1*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        try:
            canvas.drawImage('static/img/sign1.png', 650, 5, width=1.2*inch, height=0.5*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Settled by Charge Group.pdf')

def export_settled_cg_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Settled by Charge Group"

    # Define headers
    headers = ['PERIOD',
'BRANCH',
'Charge Group',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
]
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Settled by charge group.xlsx')

def export_unsettled_cg_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'PERIOD',
'BRANCH',
'Charge Group',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Unsettled by Charge Group.csv')


def export_unsettled_cg_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=10,
        leftMargin=10,
        topMargin=40,
        bottomMargin=70  # Leave space for signature and page number
    )

    elements = []

    # Try to add logo at the top
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Unsettled by Charge Group This Month </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'PERIOD', 'BRANCH', 'Charge Group', 'NUMBER_OF_BILL', 'WATER_CONS',
        'METER_RENT', 'SANITATION', 'SEWERAGE', 'VAT_AMOUNT', 'BILL_AMOUNT',
        'DEBIT_30', 'DEBIT_30_60', 'DEBIT_60', 'TOT_AMNT'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = [Paragraph(str(item) if item else '', wrap_style) for item in row]
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)

    # Footer callback
    def add_footer(canvas, doc):
        canvas.saveState()

        # Add page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(415, 15, f"Page {page_num}")

        # Optional: Add stamp and signature (images must exist)
        try:
            canvas.drawImage('static/img/teter2.png', 30, 5, width=1*inch, height=1*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        try:
            canvas.drawImage('static/img/sign1.png', 650, 5, width=1.2*inch, height=0.5*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Settled by Charge Group.pdf')

def export_unsettled_cg_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Unsettled by Charge Group"

    # Define headers
    headers = ['PERIOD',
'BRANCH',
'Charge Group',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
]
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Unettled by charge group.xlsx')







def export_delivery_route_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'PERIOD',
'BRANCH',
'ROUTE_KEY',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Delivery by route key.csv')


def export_delivery_route_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=10,
        leftMargin=10,
        topMargin=40,
        bottomMargin=70  # Leave space for signature and page number
    )

    elements = []

    # Try to add logo at the top
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Delivery by route_key This Month </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'PERIOD', 'BRANCH', 'ROUTE_KEY', 'NUMBER_OF_BILL', 'WATER_CONS',
        'METER_RENT', 'SANITATION', 'SEWERAGE', 'VAT_AMOUNT', 'BILL_AMOUNT',
        'DEBIT_30', 'DEBIT_30_60', 'DEBIT_60', 'TOT_AMNT'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = [Paragraph(str(item) if item else '', wrap_style) for item in row]
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)

    # Footer callback
    def add_footer(canvas, doc):
        canvas.saveState()

        # Add page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(415, 15, f"Page {page_num}")

        # Optional: Add stamp and signature (images must exist)
        try:
            canvas.drawImage('static/img/teter2.png', 30, 5, width=1*inch, height=1*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        try:
            canvas.drawImage('static/img/sign1.png', 650, 5, width=1.2*inch, height=0.5*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Delivery by Charge Group.pdf')

def export_delivery_route_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Delivery by Charge Group"

    # Define headers
    headers = ['PERIOD',
'BRANCH',
'ROUTE_KEY',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
]
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Delivery by route_key.xlsx')
def export_settled_route_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Delivery by Charge Group"

    # Define headers
    headers = ['PERIOD',
'BRANCH',
'ROUTE_KEY',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
]
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Settled by route_key.xlsx')

def export_settled_route_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'PERIOD',
'BRANCH',
'ROUTE_KEY',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Settled by route key.csv')

    
# def export_delivery_route_pdf(payments, branch_name='Main Branch'):
#     buffer = io.BytesIO()
#     doc = SimpleDocTemplate(
#         buffer,
#         pagesize=landscape(letter),
#         rightMargin=20,
#         leftMargin=20,
#         topMargin=40,
#         bottomMargin=20
#     )

#     elements = []
#     try:
#         logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
#         elements.append(logo)
#     except:
#         pass

#     styles = getSampleStyleSheet()
#     wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

#     title = Paragraph(f"<b>Delivery by route_key This Month </b>", styles['Title'])
#     elements.append(title)
#     elements.append(Spacer(1, 0.2 * inch))

#     headers = [
#       'PERIOD',
# 'BRANCH',
# 'ROUTE_KEY',
# 'NUMBER_OF_BILL',
# 'WATER_CONS',
# 'METER_RENT',
# 'SANITATION',
# 'SEWERAGE',
# 'VAT_AMOUNT',
# 'BILL_AMOUNT',
# 'DEBIT_30',
# 'DEBIT_30_60',
# 'DEBIT_60',
# 'TOT_AMNT'
#     ]

#     data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

#     for row in payments:
#         wrapped_row = []
#         for item in row:
#             text = str(item) if item is not None else ''
#             wrapped_row.append(Paragraph(text, wrap_style))
#         data.append(wrapped_row)

#     usable_width = landscape(letter)[0] - 40
#     col_widths = [usable_width / len(headers)] * len(headers)

#     table = Table(data, colWidths=col_widths, repeatRows=1)
#     table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.brown),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, -1), 5),
#         ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
#         ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
#         ('VALIGN', (0, 0), (-1, -1), 'TOP'),
#     ]))

#     elements.append(table)
#     doc.build(elements)
#     buffer.seek(0)

#     return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Delivery by Charge Group.pdf')

def export_settled_route_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=10,
        leftMargin=10,
        topMargin=40,
        bottomMargin=70  # Leave space for signature and page number
    )

    elements = []

    # Try to add logo at the top
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Settled by route_key This Month </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'PERIOD', 'BRANCH', 'ROUTE_KEY', 'NUMBER_OF_BILL', 'WATER_CONS',
        'METER_RENT', 'SANITATION', 'SEWERAGE', 'VAT_AMOUNT', 'BILL_AMOUNT',
        'DEBIT_30', 'DEBIT_30_60', 'DEBIT_60', 'TOT_AMNT'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = [Paragraph(str(item) if item else '', wrap_style) for item in row]
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)

    # Footer callback
    def add_footer(canvas, doc):
        canvas.saveState()

        # Add page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(415, 15, f"Page {page_num}")

        # Optional: Add stamp and signature (images must exist)
        try:
            canvas.drawImage('static/img/teter2.png', 30, 5, width=1*inch, height=1*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        try:
            canvas.drawImage('static/img/sign1.png', 650, 5, width=1.2*inch, height=0.5*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Settled by Charge Group.pdf')

def export_unsettled_route_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'PERIOD',
'BRANCH',
'ROUTE_KEY',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Unsettled by route key.csv')

    
# def export_delivery_route_pdf(payments, branch_name='Main Branch'):
#     buffer = io.BytesIO()
#     doc = SimpleDocTemplate(
#         buffer,
#         pagesize=landscape(letter),
#         rightMargin=20,
#         leftMargin=20,
#         topMargin=40,
#         bottomMargin=20
#     )

#     elements = []
#     try:
#         logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
#         elements.append(logo)
#     except:
#         pass

#     styles = getSampleStyleSheet()
#     wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

#     title = Paragraph(f"<b>Delivery by route_key This Month </b>", styles['Title'])
#     elements.append(title)
#     elements.append(Spacer(1, 0.2 * inch))

#     headers = [
#       'PERIOD',
# 'BRANCH',
# 'ROUTE_KEY',
# 'NUMBER_OF_BILL',
# 'WATER_CONS',
# 'METER_RENT',
# 'SANITATION',
# 'SEWERAGE',
# 'VAT_AMOUNT',
# 'BILL_AMOUNT',
# 'DEBIT_30',
# 'DEBIT_30_60',
# 'DEBIT_60',
# 'TOT_AMNT'
#     ]

#     data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

#     for row in payments:
#         wrapped_row = []
#         for item in row:
#             text = str(item) if item is not None else ''
#             wrapped_row.append(Paragraph(text, wrap_style))
#         data.append(wrapped_row)

#     usable_width = landscape(letter)[0] - 40
#     col_widths = [usable_width / len(headers)] * len(headers)

#     table = Table(data, colWidths=col_widths, repeatRows=1)
#     table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.brown),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, -1), 5),
#         ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
#         ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
#         ('VALIGN', (0, 0), (-1, -1), 'TOP'),
#     ]))

#     elements.append(table)
#     doc.build(elements)
#     buffer.seek(0)

#     return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Delivery by Charge Group.pdf')

def export_unsettled_route_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=10,
        leftMargin=10,
        topMargin=40,
        bottomMargin=70  # Leave space for signature and page number
    )

    elements = []

    # Try to add logo at the top
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Unsettled by route_key This Month </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'PERIOD', 'BRANCH', 'ROUTE_KEY', 'NUMBER_OF_BILL', 'WATER_CONS',
        'METER_RENT', 'SANITATION', 'SEWERAGE', 'VAT_AMOUNT', 'BILL_AMOUNT',
        'DEBIT_30', 'DEBIT_30_60', 'DEBIT_60', 'TOT_AMNT'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = [Paragraph(str(item) if item else '', wrap_style) for item in row]
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)

    # Footer callback
    def add_footer(canvas, doc):
        canvas.saveState()

        # Add page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(415, 15, f"Page {page_num}")

        # Optional: Add stamp and signature (images must exist)
        try:
            canvas.drawImage('static/img/teter2.png', 30, 5, width=1*inch, height=1*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        try:
            canvas.drawImage('static/img/sign1.png', 650, 5, width=1.2*inch, height=0.5*inch, preserveAspectRatio=True, mask='auto')
        except:
            pass

        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Unsettled by Charge Group.pdf')


def export_unsettled_route_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Unsettled by Charge Group"

    # Define headers
    headers = ['PERIOD',
'BRANCH',
'ROUTE_KEY',
'NUMBER_OF_BILL',
'WATER_CONS',
'METER_RENT',
'SANITATION',
'SEWERAGE',
'VAT_AMOUNT',
'BILL_AMOUNT',
'DEBIT_30',
'DEBIT_30_60',
'DEBIT_60',
'TOT_AMNT'
]
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Unsettled by route_key.xlsx')





def export_delivery_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "List Of Sent Bills"

    # Define headers
    headers = ['BILLKEY',
'CUSTOMERKEY',
'CUSTOMERNAME',
'CUSTOMERTIN',
'CUSTOMERBRANCH',
'REASON',
'CURRREAD',
'PREVREAD',
'CONS',
'TOTALBILLAMOUNT',
'THISMONTHBILLAMT',
'OUTSTANDINGAMT',
'PENALTYAMT',
'DRACCTNO',
'CRACCTNO']
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='paid_bills.xlsx')

def export_delivery_csv(deliverys):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'BILLKEY',
'CUSTOMERKEY',
'CUSTOMERNAME',
'CUSTOMERTIN',
'CUSTOMERBRANCH',
'REASON',
'CURRREAD',
'PREVREAD',
'CONS',
'TOTALBILLAMOUNT',
'THISMONTHBILLAMT',
'OUTSTANDINGAMT',
'PENALTYAMT',
'DRACCTNO',
'CRACCTNO'
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for delivery in deliverys:
        cw.writerow(delivery)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='delivery_bills_new.csv')


def export__delivery_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'BILLKEY',
'CUSTOMERKEY',
'CUSTOMERNAME',
'CUSTOMERTIN',
'CUSTOMERBRANCH',
'REASON',
'CURRREAD',
'PREVREAD',
'CONS',
'TOTALBILLAMOUNT',
'THISMONTHBILLAMT',
'OUTSTANDINGAMT',
'PENALTYAMT',
'DRACCTNO',
'CRACCTNO'   ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Delivery_bills.csv')
#     # Return the file as a CSV response
#     return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='paid_bills.csv')
def export_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "unmatched Bills"

    # Define headers
    headers = ['PAYMENTKEY','BILLKEY','CUSTOMERKEY','AMOUNT','BANKTXNREF','PAYMENTCHANNEL',
    'PAYMENTDATE','REQUESTID','CHANNEL','CUSTOMERNAME','CUSTOMERTIN',
    'CUSTOMERBRANCH','REASON','CURRREAD','PREVREAD','CONS','TOTALBILLAMOUNT','THISMONTHBILLAMT',
    'OUTSTANDINGAMT','PENALTYAMT','DRACCTNO','CRACCTNO','PAYMENTCOMPLETEDAT']
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='paid_bills.xlsx')

def export_csv(deliverys):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'PAYMENTKEY','BILLKEY','CUSTOMERKEY','AMOUNT','BANKTXNREF','PAYMENTCHANNEL',
    'PAYMENTDATE','REQUESTID','CHANNEL','CUSTOMERNAME','CUSTOMERTIN',
    'CUSTOMERBRANCH','REASON','CURRREAD','PREVREAD','CONS','TOTALBILLAMOUNT','THISMONTHBILLAMT',
    'OUTSTANDINGAMT','PENALTYAMT','DRACCTNO','CRACCTNO','PAYMENTCOMPLETEDAT'
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for delivery in deliverys:
        cw.writerow(delivery)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='delivery_bills_new.csv')


def export__paid_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'PAYMENTKEY','BILLKEY','CUSTOMERKEY','AMOUNT','BANKTXNREF','PAYMENTCHANNEL',
    'PAYMENTDATE','REQUESTID','CHANNEL','CUSTOMERNAME','CUSTOMERTIN',
    'CUSTOMERBRANCH','REASON','CURRREAD','PREVREAD','CONS','TOTALBILLAMOUNT','THISMONTHBILLAMT',
    'OUTSTANDINGAMT','PENALTYAMT','DRACCTNO','CRACCTNO','PAYMENTCOMPLETEDAT'    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='paid_bills.csv')
import io
import csv
from flask import send_file

def export_attendance_csv(payments):
    # Create an in-memory file with UTF-8 BOM
    si = io.StringIO()
    si.write('\ufeff')  # UTF-8 BOM

    # Initialize CSV writer
    cw = csv.writer(si)

    # Define headers (including Amharic if needed)
    headers = ['FULL_NAME', 'GENDER', 'CHRISTIAN_NAME', 'PHONE', 'SECTION_NAME', 'ATTENDANCE_DATE', 'PRESENT_STATUS']
    cw.writerow(headers)

    # Write data rows
    for payment in payments:
        cw.writerow(payment)

    # Go to the beginning
    si.seek(0)

    # Return the file
    return send_file(
        io.BytesIO(si.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='አቴንዳንስ ሪፖርት.csv'
    )

# def export_attendance_csv(payments):
#     # Create an in-memory file
#     si = io.StringIO()
#     cw = csv.writer(si)

#     # Define headers
#     headers = ['FULL_NAME','GENDER','CHRISTIAN_NAME','PHONE','SECTION_NAME','ATTENDANCE_DATE','PRESENT_STATUS'   ]
    
#     # Write the header row
#     cw.writerow(headers)
    
#     # Write the data rows
#     for payment in payments:
#         cw.writerow(payment)

#     # Move the cursor back to the start of the StringIO object
#     si.seek(0)

#     # Return the file as a CSV response
#     return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='አቴንዳንስ ሪፖርት.csv')



# CSV export function
def export_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'PAYMENTKEY','BILLKEY','CUSTOMERKEY','AMOUNT','BANKTXNREF','PAYMENTCHANNEL',
    'PAYMENTDATE','REQUESTID','CHANNEL','CUSTOMERNAME','CUSTOMERTIN',
    'CUSTOMERBRANCH','REASON','CURRREAD','PREVREAD','CONS','TOTALBILLAMOUNT','THISMONTHBILLAMT',
    'OUTSTANDINGAMT','PENALTYAMT','DRACCTNO','CRACCTNO','PAYMENTCOMPLETEDAT'    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='paid_bills.csv')

# PDF export function
# def export_paid_pdf(payments):
#     buffer = io.BytesIO()
#     # Landscape layout
#     doc = SimpleDocTemplate(
#         buffer,
#         pagesize=landscape(letter),
#         rightMargin=20,
#         leftMargin=20,
#         topMargin=20,
#         bottomMargin=20
#     )

#     headers = [
#         'PAYMENTKEY', 'BILLKEY', 'CUSTOMERKEY', 'AMOUNT', 'BANKTXNREF', 'PAYMENTCHANNEL',
#         'PAYMENTDATE', 'REQUESTID', 'CHANNEL', 'CUSTOMERNAME', 'CUSTOMERTIN',
#         'CUSTOMERBRANCH', 'REASON', 'CURRREAD', 'PREVREAD', 'CONS', 'TOTALBILLAMOUNT',
#         'THISMONTHBILLAMT', 'OUTSTANDINGAMT', 'PENALTYAMT', 'DRACCTNO', 'CRACCTNO',
#         'PAYMENTCOMPLETEDAT'
#     ]

#     data = [headers]
#     for payment in payments:
#         data.append([str(item) if item is not None else '' for item in payment])

#     # Calculate flexible column widths to fit the page width (~770 pts usable space)
#     page_width = landscape(letter)[0] - 40  # left + right margins
#     col_width = page_width / len(headers)
#     col_widths = [col_width] * len(headers)

#     table = Table(data, colWidths=col_widths)

#     # Add styling
#     table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, -1), 5),  # Smaller font to help fit data
#         ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
#         ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
#     ]))

#     doc.build([table])
#     buffer.seek(0)

#     return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='paid_bills.pdf')


# def export_paid_pdf(payments, branch_name='Main Branch'):
#     buffer = io.BytesIO()
#     doc = SimpleDocTemplate(
#         buffer,
#         pagesize=landscape(letter),
#         rightMargin=20,
#         leftMargin=20,
#         topMargin=40,
#         bottomMargin=20
#     )

#     # Add a logo (you must have a logo file path, e.g., 'static/logo.png')
#     elements = []
#     try:
#         logo = Image('static/img/AAWSA.jpg', width=1.5*inch, height=1*inch)
#         elements.append(logo)
#     except:
#         pass  # Skip if logo not found

#     # Add the header/title
#     styles = getSampleStyleSheet()
#     title = Paragraph(f"<b>Paid Bills of This Month – {branch_name}</b>", styles['Title'])
#     elements.append(title)
#     elements.append(Spacer(1, 0.2 * inch))

#     headers = [
#         'PAYMENTKEY', 'BILLKEY', 'CUSTOMERKEY', 'AMOUNT', 'BANK TXN REF', 'PAYMENT CHANNEL',
#         'PAYMENT DATE', 'REQUEST ID', 'CHANNEL', 'CUSTOMER NAME', 'CUSTOMER TIN',
#         'CUSTOMER BRANCH', 'REASON', 'CURR READ', 'PREV READ', 'CONS', 'TOTAL BILL AMOUNT',
#         'THIS MONTH BILL AMT', 'OUTSTANDING AMT', 'PENALTY AMT', 'DR ACCT NO', 'CR ACCT NO',
#         'PAYMENT COMPLETED AT'
#     ]

#     data = [headers]
#     for payment in payments:
#         data.append([str(item) if item is not None else '' for item in payment])

#     # Fit all columns in landscape letter (~770 pts of usable width)
#     usable_width = landscape(letter)[0] - 40
#     col_widths = [usable_width / len(headers)] * len(headers)

#     table = Table(data, colWidths=col_widths, repeatRows=1)

#     table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, -1), 5),
#         ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
#         ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
#         ('VALIGN', (0, 0), (-1, -1), 'TOP'),
#     ]))

#     elements.append(table)
#     doc.build(elements)
#     buffer.seek(0)

#     return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='paid_bills.pdf')






def export_unsettled_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
 'BILLKEY',
'CUSTOMERKEY',
'CUSTOMERNAME',
'CUSTOMERTIN',
'CUSTOMERBRANCH',
'REASON',
'route_key','charge_group','CONTRACT_NUMBER','METER_KEY', 
'CURRREAD',
'PREVREAD',
'CONS',
'TOTALBILLAMOUNT',
'THISMONTHBILLAMT',
'OUTSTANDINGAMT',
'PENALTYAMT',
'DRACCTNO',
'CRACCTNO','debit_30','debit_30_60','debit_60'
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='unsettled_bills.csv')

    
def export_unsettled_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=20,
        leftMargin=20,
        topMargin=40,
        bottomMargin=20
    )

    elements = []
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Unpaid  Bills of This Month </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
       'BILLKEY',
'CUSTOMERKEY',
'CUSTOMERNAME',
'CUSTOMERTIN',
'CUSTOMERBRANCH',
'REASON',
'route_key','charge_group','CONTRACT_NUMBER','METER_KEY',
'CURRREAD',
'PREVREAD',
'CONS',
'TOTALBILLAMOUNT',
'THISMONTHBILLAMT',
'OUTSTANDINGAMT',
'PENALTYAMT',
'DRACCTNO',
'CRACCTNO','debit_30','debit_30_60','debit_60'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = []
        for item in row:
            text = str(item) if item is not None else ''
            wrapped_row.append(Paragraph(text, wrap_style))
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.brown),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='unsettled_bills.pdf')
def export_unsettled_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Unsettled Bills"

    # Define headers
    headers = ['BILLKEY',
'CUSTOMERKEY',
'CUSTOMERNAME',
'CUSTOMERTIN',
'CUSTOMERBRANCH',
'REASON',
'route_key','charge_group','CONTRACT_NUMBER','METER_KEY',
'CURRREAD',
'PREVREAD',
'CONS',
'TOTALBILLAMOUNT',
'THISMONTHBILLAMT',
'OUTSTANDINGAMT',
'PENALTYAMT',
'DRACCTNO',
'CRACCTNO','debit_30','debit_30_60','debit_60']
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='unsettled_bills.xlsx')


def export_ubs_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'NAME',
               'CUST_KEY',
               'INST_KEY',
               'CONTRACT_NUMBER',
               'CHARGE_GROUP',
               'ROUTE_KEY',
               'READING_DATE',
               'BILL_KEY',
               'WALK_ORDER',
               'BRANCH',
               'PERIOD',
               'ADDRESS',
               'WATER_CONS',
               'MAINTAINANCE',
               'SEWERAGE',
               'SANITATION',
               'METER_RENT',
               'METER_KEY',
               'OLD_METER_CONS',
               'LAST_RDG_OLD_MTR',
               'PREV_RDG',
               'CURR_RDG',
               'CURR_CONS',
               'TOT_CONS',
               'CATEGORY_TYPE',
               'BLOCK1_CNS',
               'BLOCK2_CNS',
               'BLOCK3_CNS',
               'BLOCK4_CNS',
               'BLOCK5_CNS',
               'BLOCK6_CNS',
               'BLOCK7_CNS',
               'BLOCK1_TRF',
               'BLOCK2_TRF',
               'BLOCK3_TRF',
               'BLOCK4_TRF',
               'BLOCK5_TRF',
               'BLOCK6_TRF',
               'BLOCK7_TRF',
               'BLOCK1_AMNT',
               'BLOCK2_AMNT',
               'BLOCK3_AMNT',
               'BLOCK4_AMNT',
               'BLOCK5_AMNT',
               'BLOCK6_AMNT',
               'BLOCK7_AMNT',
               'METER_DIAMETER',
               'BILL_AMOUNT',
               'DEBIT_30',
               'DEBIT_30_60',
               'DEBIT_60',
               'TOT_AMNT',
               'CONS_PERIOD',
               'DUE_DATE',
               'IS_FETCHED',
               'SEND_COUNT',
               'BILL_ID',
               'INST_ID',
               'CUST_ID',
               'BILL_DATE',
               'BILL_FILE_TRAN_ID'
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Bill Delivery.csv')

    
def export_ubs_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=20,
        leftMargin=20,
        topMargin=40,
        bottomMargin=20
    )

    elements = []
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Bill Delivery of This Month </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
       'NAME',
               'CUST_KEY',
               'INST_KEY',
               'CONTRACT_NUMBER',
               'CHARGE_GROUP',
               'ROUTE_KEY',
               'READING_DATE',
               'BILL_KEY',
               'WALK_ORDER',
               'BRANCH',
               'PERIOD',
               'ADDRESS',
               'WATER_CONS',
               'MAINTAINANCE',
               'SEWERAGE',
               'SANITATION',
               'METER_RENT',
               'METER_KEY',
               'OLD_METER_CONS',
               'LAST_RDG_OLD_MTR',
               'PREV_RDG',
               'CURR_RDG',
               'CURR_CONS',
               'TOT_CONS',
               'CATEGORY_TYPE',
               'BLOCK1_CNS',
               'BLOCK2_CNS',
               'BLOCK3_CNS',
               'BLOCK4_CNS',
               'BLOCK5_CNS',
               'BLOCK6_CNS',
               'BLOCK7_CNS',
               'BLOCK1_TRF',
               'BLOCK2_TRF',
               'BLOCK3_TRF',
               'BLOCK4_TRF',
               'BLOCK5_TRF',
               'BLOCK6_TRF',
               'BLOCK7_TRF',
               'BLOCK1_AMNT',
               'BLOCK2_AMNT',
               'BLOCK3_AMNT',
               'BLOCK4_AMNT',
               'BLOCK5_AMNT',
               'BLOCK6_AMNT',
               'BLOCK7_AMNT',
               'METER_DIAMETER',
               'BILL_AMOUNT',
               'DEBIT_30',
               'DEBIT_30_60',
               'DEBIT_60',
               'TOT_AMNT',
               'CONS_PERIOD',
               'DUE_DATE',
               'IS_FETCHED',
               'SEND_COUNT',
               'BILL_ID',
               'INST_ID',
               'CUST_ID',
               'BILL_DATE',
               'BILL_FILE_TRAN_ID'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = []
        for item in row:
            text = str(item) if item is not None else ''
            wrapped_row.append(Paragraph(text, wrap_style))
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.brown),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Bill Delivery.pdf')
def export_ubs_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Unsettled Bills"

    # Define headers
    headers = ['NAME',
               'CUST_KEY',
               'INST_KEY',
               'CONTRACT_NUMBER',
               'CHARGE_GROUP',
               'ROUTE_KEY',
               'READING_DATE',
               'BILL_KEY',
               'WALK_ORDER',
               'BRANCH',
               'PERIOD',
               'ADDRESS',
               'WATER_CONS',
               'MAINTAINANCE',
               'SEWERAGE',
               'SANITATION',
               'METER_RENT',
               'METER_KEY',
               'OLD_METER_CONS',
               'LAST_RDG_OLD_MTR',
               'PREV_RDG',
               'CURR_RDG',
               'CURR_CONS',
               'TOT_CONS',
               'CATEGORY_TYPE',
               'BLOCK1_CNS',
               'BLOCK2_CNS',
               'BLOCK3_CNS',
               'BLOCK4_CNS',
               'BLOCK5_CNS',
               'BLOCK6_CNS',
               'BLOCK7_CNS',
               'BLOCK1_TRF',
               'BLOCK2_TRF',
               'BLOCK3_TRF',
               'BLOCK4_TRF',
               'BLOCK5_TRF',
               'BLOCK6_TRF',
               'BLOCK7_TRF',
               'BLOCK1_AMNT',
               'BLOCK2_AMNT',
               'BLOCK3_AMNT',
               'BLOCK4_AMNT',
               'BLOCK5_AMNT',
               'BLOCK6_AMNT',
               'BLOCK7_AMNT',
               'METER_DIAMETER',
               'BILL_AMOUNT',
               'DEBIT_30',
               'DEBIT_30_60',
               'DEBIT_60',
               'TOT_AMNT',
               'CONS_PERIOD',
               'DUE_DATE',
               'IS_FETCHED',
               'SEND_COUNT',
               'BILL_ID',
               'INST_ID',
               'CUST_ID',
               'BILL_DATE',
               'BILL_FILE_TRAN_ID'
]
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Bill Delivery.xlsx')



def export_callcenter_csv(payments):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'BILLKEY',
'CUSTOMERKEY',
'CUSTOMERNAME',
'CUSTOMERTIN',
'CUSTOMERBRANCH',
'REASON',
'CURRREAD',
'PREVREAD',
'CONS',
'TOTALBILLAMOUNT',
'THISMONTHBILLAMT',
'OUTSTANDINGAMT',
'PENALTYAMT',
'DRACCTNO',
'CRACCTNO','PHONENUMBER','route_key','charge_group','CONTRACT_NUMBER','METER_KEY' 
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for payment in payments:
        cw.writerow(payment)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='callcenter_unsettled_bills.csv')

    
def export_callcenter_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=20,
        leftMargin=20,
        topMargin=40,
        bottomMargin=20
    )

    elements = []
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Unpaid  Bills for callcenter of This Month </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
       'BILLKEY',
'CUSTOMERKEY',
'CUSTOMERNAME',
'CUSTOMERTIN',
'CUSTOMERBRANCH',
'REASON',
'CURRREAD',
'PREVREAD',
'CONS',
'TOTALBILLAMOUNT',
'THISMONTHBILLAMT',
'OUTSTANDINGAMT',
'PENALTYAMT',
'DRACCTNO',
'CRACCTNO','PHONENUMBER','route_key','charge_group','CONTRACT_NUMBER','METER_KEY'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = []
        for item in row:
            text = str(item) if item is not None else ''
            wrapped_row.append(Paragraph(text, wrap_style))
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.brown),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='callcenter_unsettled_bills.pdf')
def export_callcenter_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Unpaid Bill for Call Center "

    # Define headers
    headers = ['BILLKEY',
'CUSTOMERKEY',
'CUSTOMERNAME',
'CUSTOMERTIN',
'CUSTOMERBRANCH',
'REASON',
'CURRREAD',
'PREVREAD',
'CONS',
'TOTALBILLAMOUNT',
'THISMONTHBILLAMT',
'OUTSTANDINGAMT',
'PENALTYAMT',
'DRACCTNO',
'CRACCTNO','PHONENUMBER','route_key','charge_group','CONTRACT_NUMBER','METER_KEY']
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='unpaid For Call Center.xlsx')




# from reportlab.lib.styles import ParagraphStyle

def export_paid_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=20,
        leftMargin=20,
        topMargin=40,
        bottomMargin=20
    )

    elements = []
    try:
        logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>Paid Bills of This Month </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'PAYMENTKEY', 'BILLKEY', 'CUSTOMERKEY', 'AMOUNT', 'BANK TXN REF', 'PAYMENT CHANNEL',
        'PAYMENT DATE', 'REQUEST ID', 'CHANNEL', 'CUSTOMER NAME', 'CUSTOMER TIN',
        'CUSTOMER BRANCH', 'REASON', 'CURR READ', 'PREV READ', 'CONS', 'TOTAL BILL AMOUNT',
        'THIS MONTH BILL AMT', 'OUTSTANDING AMT', 'PENALTY AMT', 'DR ACCT NO', 'CR ACCT NO',
        'PAYMENT COMPLETED AT'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = []
        for item in row:
            text = str(item) if item is not None else ''
            wrapped_row.append(Paragraph(text, wrap_style))
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.brown),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='paid_bills.pdf')


# def export_paid_pdf(payments, branch_name='Main Branch'):
#     buffer = io.BytesIO()
#     doc = SimpleDocTemplate(
#         buffer,
#         pagesize=landscape(letter),
#         rightMargin=20,
#         leftMargin=20,
#         topMargin=40,
#         bottomMargin=20
#     )

#     elements = []

#     # Try to add logo
#     try:
#         logo = Image('static/img/AAWSA.jpg', width=1 * inch, height=1 * inch)
#         elements.append(logo)
#     except:
#         pass

#     # Title
#     styles = getSampleStyleSheet()
#     wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)
#     title = Paragraph(f"<b>Paid Bills of This Month – {branch_name}</b>", styles['Title'])
#     elements.append(title)
#     elements.append(Spacer(1, 0.2 * inch))

#     # Headers
#     headers = [
#         'PAYMENTKEY', 'BILLKEY', 'CUSTOMERKEY', 'AMOUNT', 'BANK TXN REF', 'PAYMENT CHANNEL',
#         'PAYMENT DATE', 'REQUEST ID', 'CHANNEL', 'CUSTOMER NAME', 'CUSTOMER TIN',
#         'CUSTOMER BRANCH', 'REASON', 'CURR READ', 'PREV READ', 'CONS', 'TOTAL BILL AMOUNT',
#         'THIS MONTH BILL AMT', 'OUTSTANDING AMT', 'PENALTY AMT', 'DR ACCT NO', 'CR ACCT NO',
#         'PAYMENT COMPLETED AT'
#     ]

#     # Prepare data
#     data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

#     # Indexes of long text fields to wrap
#     wrap_indexes = [4, 5, 6, 7, 8, 9, 10, 11, 12, 22]  # Adjust as needed

#     usable_width = landscape(letter)[0] - 40
#     col_widths = [usable_width / len(headers)] * len(headers)

#     for row in payments:
#         wrapped_row = []
#         for i, item in enumerate(row):
#             text = str(item) if item is not None else ''
#             if i in wrap_indexes:
#                 wrapped_row.append(KeepInFrame(
#                     col_widths[i],
#                     0.25 * inch,
#                     [Paragraph(text, wrap_style)],
#                     mode='shrink'
#                 ))
#             else:
#                 wrapped_row.append(text)
#         data.append(wrapped_row)

#     # Build table
#     table = Table(data, colWidths=col_widths, repeatRows=1)
#     table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, -1), 5),
#         ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
#         ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
#         ('VALIGN', (0, 0), (-1, -1), 'TOP'),
#     ]))

#     elements.append(table)
#     doc.build(elements)
#     buffer.seek(0)

#     return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='paid_bills.pdf')



# Excel export function

def attendance_report_pdf(payments, branch_name='Main Branch'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=20,
        leftMargin=20,
        topMargin=40,
        bottomMargin=20
    )

    elements = []
    try:
        logo = Image('static/img/download.jpg', width=1 * inch, height=1 * inch)
        elements.append(logo)
    except:
        pass

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('wrap', fontSize=7, leading=6)

    title = Paragraph(f"<b>የአቴንዳንስ ሪፖርት </b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'FULL_NAME','GENDER','CHRISTIAN_NAME','PHONE','SECTION_NAME','ATTENDANCE_DATE','PRESENT_STATUS'
    ]

    data = [[Paragraph(f"<b>{col}</b>", wrap_style) for col in headers]]

    for row in payments:
        wrapped_row = []
        for item in row:
            text = str(item) if item is not None else ''
            wrapped_row.append(Paragraph(text, wrap_style))
        data.append(wrapped_row)

    usable_width = landscape(letter)[0] - 40
    col_widths = [usable_width / len(headers)] * len(headers)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.brown),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='የአቴንዳንስ ሪፖርት.pdf')
def attendance_report_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "የአቴንዳንስ ሪፖርት"

    # Define headers
    headers = ['FULL_NAME','GENDER','CHRISTIAN_NAME','PHONE','SECTION_NAME','ATTENDANCE_DATE','PRESENT_STATUS']
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='የአቴንዳንስ ሪፖርት.xlsx')


def export_paid_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Paid Bills"

    # Define headers
    headers = ['PAYMENTKEY','BILLKEY','CUSTOMERKEY','AMOUNT','BANKTXNREF','PAYMENTCHANNEL',
    'PAYMENTDATE','REQUESTID','CHANNEL','CUSTOMERNAME','CUSTOMERTIN',
    'CUSTOMERBRANCH','REASON','CURRREAD','PREVREAD','CONS','TOTALBILLAMOUNT','THISMONTHBILLAMT',
    'OUTSTANDINGAMT','PENALTYAMT','DRACCTNO','CRACCTNO','PAYMENTCOMPLETEDAT']
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='paid_bills.xlsx')

def export_csv(deliverys):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'PAYMENTKEY','BILLKEY','CUSTOMERKEY','AMOUNT','BANKTXNREF','PAYMENTCHANNEL',
    'PAYMENTDATE','REQUESTID','CHANNEL','CUSTOMERNAME','CUSTOMERTIN',
    'CUSTOMERBRANCH','REASON','CURRREAD','PREVREAD','CONS','TOTALBILLAMOUNT','THISMONTHBILLAMT',
    'OUTSTANDINGAMT','PENALTYAMT','DRACCTNO','CRACCTNO','PAYMENTCOMPLETEDAT'
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for delivery in deliverys:
        cw.writerow(delivery)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='delivery_bills_new.csv')

# PDF export function
def export_pdf(deliverys):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    data = []
    headers = ['PAYMENTKEY','BILLKEY','CUSTOMERKEY','AMOUNT','BANKTXNREF','PAYMENTCHANNEL',
    'PAYMENTDATE','REQUESTID','CHANNEL','CUSTOMERNAME','CUSTOMERTIN',
    'CUSTOMERBRANCH','REASON','CURRREAD','PREVREAD','CONS','TOTALBILLAMOUNT','THISMONTHBILLAMT',
    'OUTSTANDINGAMT','PENALTYAMT','DRACCTNO','CRACCTNO','PAYMENTCOMPLETEDAT'

]
    data.append(headers)
    
    for delivery in deliverys:
        data.append(delivery)

    # Define column widths to ensure data fits
    col_widths = [1.5 * inch] * len(headers)  # Adjust the width as needed
    
    table = Table(data, colWidths=col_widths)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDSPACE', (0, 1), (-1, -1), 10)  # Adjust word spacing if needed
    ]))

    doc.build([table])
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='delivery_bills.pdf')



# Excel export function
def export_excel(deliverys):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Delivery Bills"

    # Define headers
    headers = ['PAYMENTKEY',
'PAYMENTKEY','BILLKEY','CUSTOMERKEY','AMOUNT','BANKTXNREF','PAYMENTCHANNEL',
    'PAYMENTDATE','REQUESTID','CHANNEL','CUSTOMERNAME','CUSTOMERTIN',
    'CUSTOMERBRANCH','REASON','CURRREAD','PREVREAD','CONS','TOTALBILLAMOUNT','THISMONTHBILLAMT',
    'OUTSTANDINGAMT','PENALTYAMT','DRACCTNO','CRACCTNO','PAYMENTCOMPLETEDAT']
    ws.append(headers)

    # Write the data rows
    for delivery in deliverys:
        ws.append(delivery)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='delivery_bills.xlsx')

def export_excel(call_center_unsettleds):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Delivery Bills"

    # Define headers
    headers = [
        'PAYMENTKEY','BILLKEY','CUSTOMERKEY','AMOUNT','BANKTXNREF','PAYMENTCHANNEL',
    'PAYMENTDATE','REQUESTID','CHANNEL','CUSTOMERNAME','CUSTOMERTIN',
    'CUSTOMERBRANCH','REASON','CURRREAD','PREVREAD','CONS','TOTALBILLAMOUNT','THISMONTHBILLAMT',
    'OUTSTANDINGAMT','PENALTYAMT','DRACCTNO','CRACCTNO','PAYMENTCOMPLETEDAT'

]
    ws.append(headers)

    # Write the data rows
    for call_center_unsettled in call_center_unsettleds:
        ws.append(call_center_unsettled)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Unpaid Bills With Phone Number.xlsx')

def export_csv(call_center_unsettleds):
    # Create an in-memory file
    si = io.StringIO()
    cw = csv.writer(si)

    # Define headers
    headers = [
'PAYMENTKEY','BILLKEY','CUSTOMERKEY','AMOUNT','BANKTXNREF','PAYMENTCHANNEL',
    'PAYMENTDATE','REQUESTID','CHANNEL','CUSTOMERNAME','CUSTOMERTIN',
    'CUSTOMERBRANCH','REASON','CURRREAD','PREVREAD','CONS','TOTALBILLAMOUNT','THISMONTHBILLAMT',
    'OUTSTANDINGAMT','PENALTYAMT','DRACCTNO','CRACCTNO','PAYMENTCOMPLETEDAT'
    
    ]
    
    # Write the header row
    cw.writerow(headers)
    
    # Write the data rows
    for call_center_unsettled in call_center_unsettleds:
        cw.writerow(call_center_unsettled)

    # Move the cursor back to the start of the StringIO object
    si.seek(0)

    # Return the file as a CSV response
    return send_file(io.BytesIO(si.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='delivery_bills.csv')

# PDF export function
def export_pdf(call_center_unsettleds):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A3), rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=18)
    
    data = []
    headers = [
        'BILLKEY',
'CUSTOMERKEY',
'CUSTOMERNAME',
'CUSTOMERTIN',
'CUSTOMERBRANCH',
'REASON',
'CURRREAD',
'PREVREAD',
'CONS',
'TOTALBILLAMOUNT',
'THISMONTHBILLAMT',
'OUTSTANDINGAMT',
'PENALTYAMT',
'DRACCTNO',
'CRACCTNO',
'PHONENUMBER'
]
    data.append(headers)
    
    for call_center_unsettled in call_center_unsettleds:
        data.append(call_center_unsettled)

    # Define column widths to ensure data fits
    col_widths = [1.5 * inch] * len(headers)  # Adjust the width as needed
    
    table = Table(data, colWidths=col_widths)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGRO UND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDSPACE', (0, 1), (-1, -1), 10)  # Adjust word spacing if needed
    ]))

    doc.build([table])
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='Unsettled With Phone Number.pdf')



# Excel export function
def export_excel(call_center_unsettleds):
    # Create a workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Unsettled For Call center Bills"

    # Define headers
    headers = ['BILLKEY',
'CUSTOMERKEY',
'CUSTOMERNAME',
'CUSTOMERTIN',
'CUSTOMERBRANCH',
'REASON',
'CURRREAD',
'PREVREAD',
'CONS',
'TOTALBILLAMOUNT',
'THISMONTHBILLAMT',
'OUTSTANDINGAMT',
'PENALTYAMT',
'DRACCTNO',
'CRACCTNO',
'PHONENUMBER']
    ws.append(headers)

    # Write the data rows
    for call_center_unsettled in call_center_unsettleds:
        ws.append(call_center_unsettled)

    # Save the workbook to an in-memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return the file as an Excel response
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='unsettled with Phone number.xlsx')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/move_data', methods=['GET', 'POST'])
@login_required
# @login_required
@role_required('Super Admin') 
def move_data():
    if request.method == 'POST':
        payroll_number = request.form['payroll_number']
        password = request.form['password']
        action_type = request.form['action_type']  # Can be 'payment' or 'bill'
        
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # Verify payroll_number and password from the 'aawsa_user' table
            cursor.execute("""
                SELECT COUNT(*) FROM aawsa_user WHERE payroll_number = :payroll_number AND password = :password
            """, {'payroll_number': payroll_number, 'password': password})
            
            user_exists = cursor.fetchone()[0]

            if user_exists:
                if action_type == 'payment':
                    # Move payment data
                    cursor.execute("""
                        INSERT INTO PAYMENT_OLD (SELECT * FROM PAYMENT)
                    """)
                    cursor.execute("""
                        DELETE FROM PAYMENT
                    """)
                    connection.commit()
                    return render_template('move_data.html', message="Payment data moved and deleted successfully")
                
                elif action_type == 'bill':
                    # Move bill data
                    cursor.execute("""
                        INSERT INTO BILL_OLD (SELECT * FROM BILL)
                    """)
                    cursor.execute("""
                        DELETE FROM BILL
                    """)
                    connection.commit()
                    return render_template('move_data.html', message="Bill data moved and deleted successfully")
                
                else:
                    return render_template('move_data.html', error="Invalid action type")
            else:
                return render_template('move_data.html', error="Invalid Payroll Number or Password")

        except Exception as e:
            connection.rollback()
            return render_template('move_data.html', error=str(e))

        finally:
            connection.close()

    # If the request method is GET, just render the form page
    return render_template('move_data.html')

def execute_query(query):
    """
    Executes the given query and returns the result.
    """
    connection = cx_Oracle.connect("agresso/agressotest@localhost:1522/orcl2")  # Adjust connection string if needed
    cursor = connection.cursor()  # Create a cursor
    cursor.execute(query)  # Execute the query
    result = cursor.fetchall()  # Fetch all the results
    cursor.close()  # Close the cursor
    connection.close()  # Close the connection
    return result

def get_branches():
    """
    Retrieves the list of distinct branches from the BILL table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT DISTINCT CUSTOMERBRANCH FROM BILL ORDER BY CUSTOMERBRANCH"
    cursor.execute(query)
    branches = cursor.fetchall()
    cursor.close()
    conn.close()
    return [branch[0] for branch in branches]  # Extract the branch names from the tuple

def get_branches_ubs():
    """
    Retrieves the list of distinct branches from the BILL table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT DISTINCT BRANCH FROM bill_table_ubs ORDER BY BRANCH"
    cursor.execute(query)
    branches = cursor.fetchall()
    cursor.close()
    conn.close()
    return [branch[0] for branch in branches] 

@app.route('/reports')
@login_required
def report_page():
    branches = get_branches()  # Get list of branches for the filter

    # Fetching delivery report data
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetching delivery report data
    query_delivery = """
    SELECT CUSTOMERBRANCH AS branch, COUNT(*) AS total_bills,
           SUM(TOTALBILLAMOUNT) AS sum_total_bills,
           SUM(CONS) AS sum_consumption
    FROM BILL
    GROUP BY rollup(CUSTOMERBRANCH)
    """
    cursor.execute(query_delivery)
    delivery_report_data = cursor.fetchall()

    # Fetching paid bills summary data
    query_paid_bills_summary = """
  SELECT CUSTOMERBRANCH as branch,COUNT(*) AS total_paid_bills,
           SUM(TOTALBILLAMOUNT) AS sum_total_bills,
           SUM(CONS) AS sum_consumption
    FROM PAYMENT a, BILL b where a.BILLKEY=b.BILLKEY group by rollup(CUSTOMERBRANCH)
    """
    cursor.execute(query_paid_bills_summary)
    paid_bills_summary_data = cursor.fetchall()

    # Fetching unsettled bills summary data
    query_unsettled_summary = """
    SELECT  CUSTOMERBRANCH as branch,COUNT(*) AS total_unsettled_bills,
           SUM(TOTALBILLAMOUNT) AS sum_total_unsettled_amount,
           SUM(CONS) AS sum_consumption
    FROM BILL b
    where BILLKEY not in (select BILLKEY from payment) group by rollup(CUSTOMERBRANCH)
    """
    cursor.execute(query_unsettled_summary)
    unsettled_summary_data = cursor.fetchall()
    
    cursor.close()
    conn.close()

    # Debugging: Print the fetched data
    # print("Delivery Report Data:", delivery_report_data)
    # print("Paid Bills Summary Data:", paid_bills_summary_data)
    # print("Unsettled Summary Data:", unsettled_summary_data)

    # Format data for the template
    formatted_delivery_data = [
        {'branch': row[0], 'total_bills': row[1], 'sum_total_bills': row[2], 'sum_consumption': row[3]}
        for row in delivery_report_data
    ]

    
    
    formatted_paid_bills_summary = [
        {'branch': row[0],
        'total_paid_bills': row[1],
        'sum_total_paid_amount': row[2],
        'sum_consumption': row[3]
        }
        for row in paid_bills_summary_data
    ]

    formatted_unsettled_summary = [
        {'branch': row[0],
        'total_unsettled_bills': row[1],
        'sum_total_unsettled_amount': row[2],
        'sum_consumption': row[3]}
        for row in unsettled_summary_data
    ]


    return render_template('reports.html', branches=branches, delivery_data=formatted_delivery_data,
                           paid_bills_summary=formatted_paid_bills_summary, unsettled_summary=formatted_unsettled_summary)


@app.route('/report/delivery')
@login_required
def delivery_report():
    # Fetch the data for the delivery report
    delivery_data = get_delivery_report_data()  # You need to write this query to fetch the required data
    return render_template('delivery_report.html', data=delivery_data)

@app.route('/report/paid_bills')
@login_required
def paid_bills_report():
    # Fetch the data for the paid bills report
    paid_bills_data = get_paid_bills_report_data()  # Query to fetch paid bills grouped by branch
    return render_template('paid_bills_report.html', data=paid_bills_data)

@app.route('/report/unsettled_bills')
@login_required
def unsettled_bills_report():
    # Fetch the data for the unsettled bills report (bills not in the payment table)
    unsettled_bills_data = get_unsettled_bills_report_data()
    return render_template('unsettled_bills_report.html', data=unsettled_bills_data)

@app.route('/export/<report_type>/<file_format>')
@login_required
def export_report(report_type, file_format):
    
    # Fetch the data for the report type
    data = get_report_data(report_type)
    
    if data is None or len(data) == 0:
        return "No data available for the specified report type.", 404  # Handle no data case
    
    # Convert list to DataFrame
    if isinstance(data, list):
        data = pd.DataFrame(data)

    if file_format == 'csv':
        output = BytesIO()
        data.columns = ['Branch', 'Total Bills', 'Sum of Total Bills', 'Sum of Consumption']
        data.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, mimetype='text/csv', download_name=f"{report_type}.csv", as_attachment=True)
    
    elif file_format == 'excel':
        output = BytesIO()
        # data.columns = ['Branch', 'Total Bills', 'Sum of Total Bills', 'Sum of Consumption']
        data.columns = ['Branch', 'Total Bills', 'Sum of Total Bills', 'Sum of Consumption']
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:  # Use a context manager
            data.to_excel(writer, index=False)
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name=f"{report_type}.xlsx", as_attachment=True)
    elif file_format == 'pdf':
    # Create a PDF document
        pdf = FPDF()
        pdf.add_page()

        # Set title
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, 'Report', 0, 1, 'C')

        # Check DataFrame columns
        print(data.columns.tolist())  # Print column names for debugging

        # Add table header
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 10, 'Branch', 1)
        pdf.cell(40, 10, 'Total Bills', 1)
        pdf.cell(40, 10, 'Sum of Total Bills', 1)
        pdf.cell(40, 10, 'Sum of Consumption', 1)
        pdf.ln()

        # Add data to PDF
        pdf.set_font("Arial", '', 10)
        for index, row in data.iterrows():
            branch_name = row.get('Branch', 'N/A')  # Access column safely
            total_bills = row.get('Total Bills', 'N/A')
            sum_of_total_bills = row.get('Sum of Total Bills', 'N/A')
            sum_of_consumption = row.get('Sum of Consumption', 'N/A')

            pdf.cell(40, 10, str(branch_name), 1)
            pdf.cell(40, 10, str(total_bills), 1)
            pdf.cell(40, 10, str(sum_of_total_bills), 1)
            pdf.cell(40, 10, str(sum_of_consumption), 1)
            pdf.ln()

        # Use a temporary file to save the PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf.output(tmp_file.name)  # Save the PDF to the temporary file
            tmp_file.seek(0)  # Move to the beginning of the temporary file
            # Read the PDF into a BytesIO object
            output = BytesIO(tmp_file.read())

        # Return the PDF as a response
        return send_file(output, as_attachment=True, download_name='report.pdf', mimetype='application/pdf')
        # Handle unsupported file formats

def get_report_data(report_type):
    if report_type == 'delivery':
        return get_delivery_report_data()
    elif report_type == 'paid_bills':
        return get_paid_bills_report_data()
    elif report_type == 'unsettled_bills':
        return get_unsettled_bills_report_data()
    else:
        raise ValueError("Unknown report type")

def get_delivery_report_data():
    query = """
    SELECT CUSTOMERBRANCH AS branch, COUNT(*) AS total_bills,
           SUM(TOTALBILLAMOUNT) AS sum_total_bills,
           SUM(CONS) AS sum_consumption
    FROM BILL
    GROUP BY rollup(CUSTOMERBRANCH)
    """
    results = execute_query(query)  # Execute the query
    if results is None:
        print("No results returned from execute_query for delivery report.")  # Debug print
        return []
    return results  # Ensure this returns a list
    # return execute_query(query)  # Assuming you have a DB query execution function

def get_paid_bills_report_data():
    query = """
     SELECT CUSTOMERBRANCH as branch,COUNT(*) AS total_paid_bills,
           SUM(TOTALBILLAMOUNT) AS sum_total_bills,
           SUM(CONS) AS sum_consumption
    FROM PAYMENT a, BILL b where a.BILLKEY=b.BILLKEY group by rollup(CUSTOMERBRANCH)
    """
    return execute_query(query)

def get_unsettled_bills_report_data():
    query = """
     SELECT  CUSTOMERBRANCH as branch,COUNT(*) AS total_unsettled_bills,
           SUM(TOTALBILLAMOUNT) AS sum_total_unsettled_amount,
           SUM(CONS) AS sum_consumption
    FROM BILL b
    where BILLKEY not in (select BILLKEY from payment) group by rollup(CUSTOMERBRANCH)
    """
    return execute_query(query)

# Helper function to execute SQL queries
# def execute_query(query):
#     connection = get_db_connection()  # Assuming this function connects to your DB
#     result = connection.execute(query).fetchall()
#     connection.close()
#     return result

def execute_query(query):
    connection = get_db_connection()  # Get the DB connection
    if connection is None:
        print("Failed to connect to the database.")
        return None

    try:
        cursor = connection.cursor()  # Create a cursor object
        cursor.execute(query)          # Execute the SQL query
        result = cursor.fetchall()     # Fetch all results
        return result
    except Exception as e:
        print(f"Error executing query: {e}")
        return None
    finally:
        cursor.close()                # Ensure the cursor is closed
        connection.close()    


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
            WHERE username = :username OR payroll_number = :payroll_number
        """, {'username': form_data['username'], 'payroll_number': form_data['payroll_number']})
        
        if cursor.fetchone():
            flash('Username or payroll number already exists!', 'danger')
        else:
            # Verify role exists
            cursor.execute("SELECT 1 FROM roles WHERE role_id = :role_id", {'role_id': form_data['role_id']})
            if not cursor.fetchone():
                flash('Invalid role selected!', 'danger')
            else:
                # Insert new user
                cursor.execute("""
                    INSERT INTO aawsa_user (username, password, payroll_number, branch, role_id)
                    VALUES (:username, :password, :payroll_number, :branch, :role_id)
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
                SET username = :username,
                    payroll_number = :payroll_number,
                    branch = :branch,
                    role_id = :role_id
                WHERE user_id = :user_id
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
            WHERE user_id = :user_id
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
        cursor.execute("DELETE FROM aawsa_user WHERE user_id = :user_id", {'user_id': user_id})
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

@app.route('/upload_bill', methods=['GET', 'POST'])
@login_required
# @login_required
@role_required('Super Admin') 
def upload_bill():
    if request.method == 'POST':
        file = request.files['file']
        if not file or not file.filename.endswith('.csv'):
            flash("Please upload a valid CSV file.", "danger")
            return redirect('/upload_bill')

        connection = get_db_connection()
        cursor = connection.cursor()

        duplicate_bill_keys = set()  # Using set for faster lookups
        inserted_count = 0
        csv_bill_keys = set()
        rows = []

        # Define the expected column order
        COLUMNS = [
            'BILLKEY', 'CUSTOMERKEY', 'CUSTOMERNAME', 'CUSTOMERTIN', 'CUSTOMERBRANCH',
            'REASON', 'CURRREAD', 'PREVREAD', 'CONS', 'TOTALBILLAMOUNT',
            'THISMONTHBILLAMT', 'OUTSTANDINGAMT', 'PENALTYAMT', 'DRACCTNO', 'CRACCTNO'
        ]

        try:
            # Process the file in memory for faster access
            file_content = file.stream.read().decode('utf-8').splitlines()
            reader = csv.reader(file_content)
            
            # Skip header if exists
            next(reader, None)

            # Single pass processing with immediate duplicate checking
            for row in reader:
                if not row:
                    continue

                try:
                    row_dict = dict(zip(COLUMNS, row))
                    bill_key = row_dict['BILLKEY']

                    # Check for duplicates in CSV first
                    if bill_key in csv_bill_keys:
                        duplicate_bill_keys.add(bill_key)
                        continue

                    csv_bill_keys.add(bill_key)
                    rows.append(row_dict)
                except (IndexError, KeyError) as e:
                    app.logger.warning(f"Skipping malformed row: {row}. Error: {str(e)}")
                    continue

            # Bulk check for existing keys in database
            if rows:
                # Use batches to avoid too many parameters (Oracle has a limit)
                batch_size = 1000
                existing_keys = set()
                
                for i in range(0, len(csv_bill_keys), batch_size):
                    batch = list(csv_bill_keys)[i:i + batch_size]
                    placeholders = ', '.join([':key'+str(i) for i in range(len(batch))])
                    params = {'key'+str(i): key for i, key in enumerate(batch)}
                    
                    cursor.execute(f"SELECT BILLKEY FROM BILL WHERE BILLKEY IN ({placeholders})", params)
                    existing_keys.update(row[0] for row in cursor.fetchall())

                # Filter and prepare for insert
                unique_rows = []
                for row in rows:
                    if row['BILLKEY'] in existing_keys:
                        duplicate_bill_keys.add(row['BILLKEY'])
                    else:
                        unique_rows.append(row)

                # Bulk insert in batches
                if unique_rows:
                    insert_sql = """
                        INSERT INTO BILL (
                            BILLKEY, CUSTOMERKEY, CUSTOMERNAME, CUSTOMERTIN, CUSTOMERBRANCH, 
                            REASON, CURRREAD, PREVREAD, CONS, TOTALBILLAMOUNT, 
                            THISMONTHBILLAMT, OUTSTANDINGAMT, PENALTYAMT, DRACCTNO, CRACCTNO
                        ) VALUES (
                            :BILLKEY, :CUSTOMERKEY, :CUSTOMERNAME, :CUSTOMERTIN, :CUSTOMERBRANCH, 
                            :REASON, :CURRREAD, :PREVREAD, :CONS, :TOTALBILLAMOUNT, 
                            :THISMONTHBILLAMT, :OUTSTANDINGAMT, :PENALTYAMT, :DRACCTNO, :CRACCTNO
                        )
                    """
                    
                    # Insert in batches to avoid memory issues
                    for i in range(0, len(unique_rows), batch_size):
                        batch = unique_rows[i:i + batch_size]
                        cursor.executemany(insert_sql, batch)
                    
                    inserted_count = len(unique_rows)
                    connection.commit()
                    flash(f"Successfully uploaded {inserted_count} bills!", "success")
                else:
                    flash("No unique bill data to upload.", "warning")

            # Prepare duplicate message
            if duplicate_bill_keys:
                dup_count = len(duplicate_bill_keys)
                sample_duplicates = ', '.join(list(duplicate_bill_keys)[:5])
                if dup_count > 5:
                    sample_duplicates += f" and {dup_count-5} more"
                flash(f"Skipped {dup_count} duplicate bill keys (sample: {sample_duplicates})", "info")

        except Exception as e:
            connection.rollback()
            flash(f"Error uploading bill data: {str(e)}", "danger")
            app.logger.error(f"Error in upload_bill: {str(e)}", exc_info=True)
        
        finally:
            cursor.close()
            connection.close()

        return redirect('/upload_bill')

    return render_template('upload_bill.html')
@app.route('/bulk-payments', methods=['GET', 'POST'])
def bulk_payments():
    if request.method == 'POST':
        try:
            batch_size = int(request.form.get('batch_size', 100))
            max_retries = int(request.form.get('max_retries', 3))

            conn = get_db_connection()
            cursor = conn.cursor()

            # Call the stored procedure
            cursor.callproc('process_bulk_payments', [batch_size, max_retries])

            # Fetch the most recent batch result
            cursor.execute("""
                SELECT 
                    batch_id,
                    TO_CHAR(start_time, 'YYYY-MM-DD HH24:MI:SS') AS start_time,
                    TO_CHAR(end_time, 'YYYY-MM-DD HH24:MI:SS') AS end_time,
                    batch_size,
                    success_count,
                    failure_count,
                    status,
                    error_message
                FROM payment_batch_log 
                WHERE batch_id = (SELECT MAX(batch_id) FROM payment_batch_log)
            """)

            batch_data = cursor.fetchone()

            if batch_data:
                # Explicitly use correct column names (uppercase as Oracle returns)
                columns = [col[0].lower() for col in cursor.description]
                batch_result = dict(zip(columns, batch_data))

                # Check if batch_id exists in dictionary
                if 'batch_id' in batch_result:
                    flash(
                        f"Bulk processing completed: {batch_result.get('success_count', 0)} succeeded, "
                        f"{batch_result.get('failure_count', 0)} failed",
                        'success'
                    )
                    return redirect(url_for('bulk_payment_results', batch_id=batch_result['batch_id']))
                else:
                    flash('Batch ID not found in results.', 'danger')
            else:
                flash('No batch results found.', 'warning')

        except Exception as e:
            flash(f'Error processing bulk payments: {str(e)}', 'danger')
            app.logger.error(f"Bulk payment error: {str(e)}", exc_info=True)

        finally:
            cursor.close()
            conn.close()

        return redirect(request.url)

    return render_template('bulk_payments.html')
@app.route('/upload_payment_unsent', methods=['GET', 'POST'])
def upload_payment_unsent():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash("No file selected", "warning")
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash("Please upload a CSV file", "warning")
            return redirect(request.url)

        # Read CSV file content as text
        data = file.read().decode('utf-8')
        csv_reader = csv.DictReader(StringIO(data))

        records = []
        for row in csv_reader:
            # Basic validation: ensure required columns exist and are not empty
            if not row.get('banktxnref') or not row.get('amount') or not row.get('billkey'):
                flash("Missing required fields (banktxnref, amount, billkey) in CSV", "danger")
                return redirect(request.url)
            try:
                amount = float(row['amount'])
            except ValueError:
                flash(f"Invalid amount value: {row['amount']}", "danger")
                return redirect(request.url)
            
            records.append({
                'banktxnref': row['banktxnref'],
                'amount': amount,
                'channel': row.get('channel'),
                'billkey': row['billkey'],
                'paymentchannel': row.get('paymentchannel'),
                'payment_date': row.get('payment_date')
            })

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            for rec in records:
                cursor.execute("""
                    INSERT INTO payment_unsent (
                        banktxnref, amount, channel, billkey, paymentchannel, payment_date
                    ) VALUES (
                        :banktxnref, :amount, :channel, :billkey, :paymentchannel, :payment_date
                    )
                """, rec)
            conn.commit()
            flash(f"Successfully inserted {len(records)} records.", "success")
        except Exception as e:
            flash(f"Error inserting data: {str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('upload_payment_unsent'))

    return render_template('upload_payment_unsent.html')
# @app.route('/add_payment_unsent', methods=['GET', 'POST'])
# def add_payment_unsent():
#     if request.method == 'POST':
#         banktxnref = request.form.get('banktxnref')
#         amount = request.form.get('amount')
#         channel = request.form.get('channel')
#         billkey = request.form.get('billkey')
#         paymentchannel = request.form.get('paymentchannel')
#         payment_date = request.form.get('payment_date')

#         # Basic validation
#         if not (banktxnref and amount and billkey):
#             flash("BankTxnRef, Amount, and BillKey are required fields.", "warning")
#             return redirect(url_for('add_payment_unsent'))

#         try:
#             amount = float(amount)
#         except ValueError:
#             flash("Amount must be a valid number.", "warning")
#             return redirect(url_for('add_payment_unsent'))

#         conn = get_db_connection()
#         cursor = conn.cursor()
#         try:
#             cursor.execute("""
#                 INSERT INTO payment_unsent (
#                     banktxnref, amount, channel, billkey, paymentchannel, payment_date
#                 ) VALUES (
#                     :banktxnref, :amount, :channel, :billkey, :paymentchannel, :payment_date
#                 )
#             """, {
#                 'banktxnref': banktxnref,
#                 'amount': amount,
#                 'channel': channel,
#                 'billkey': billkey,
#                 'paymentchannel': paymentchannel,
#                 'payment_date': payment_date
#             })
#             conn.commit()
#             flash("Payment unsent record inserted successfully!", "success")
#             return redirect(url_for('add_payment_unsent'))
#         except Exception as e:
#             flash(f"Error inserting data: {str(e)}", "danger")
#         finally:
#             cursor.close()
#             conn.close()

#     return render_template('add_payment_unsent.html')


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
                        education, rank, education_status, work, student,
                        career, marital_status
                    ) VALUES (
                        :full_name, :father_of_repentance, :mother_name, :parish, :christian_name,
                        :age_of_birth, :subcity, :woreda, :house_number, :special_place,
                        :phone, :leving, :work_status, :email, :member_year,
                        :education, :rank, :education_status, :work, :student,
                        :career, :marital_status
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
# @app.route('/manage_members', methods=['GET', 'POST'])
# def manage_members():
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     if request.method == 'POST':
#         # Create or Update record
#         form_data = request.form.to_dict()
#         member_id = form_data.get('id')

#         if member_id:  # Update
#             query = """
#                 UPDATE member_registration  SET full_name=:full_name, father_of_repentance=:father_of_repentance,
#                 mother_name=:mother_name, parish=:parish, christian_name=:christian_name,
#                 age_of_birth=:age_of_birth, subcity=:subcity, woreda=:woreda, house_number=:house_number,
#                 special_place=:special_place, phone=:phone, leving=:leving, work_status=:work_status,
#                 email=:email, member_year=:member_year, spiritual_education=:spiritual_education,
#                 rank=:rank, education_status=:education_status, work=:work, student=:student,
#                 career=:career, marital_status=:marital_status
#                 WHERE id=:id
#             """
#         else:  # Create
#             query = """
#                 INSERT INTO member_registration  (
#                     full_name, father_of_repentance, mother_name, parish, christian_name,
#                     age_of_birth, subcity, woreda, house_number, special_place,
#                     phone, leving, work_status, email, member_year, spiritual_education,
#                     rank, education_status, work, student, career, marital_status
#                 ) VALUES (
#                     :full_name, :father_of_repentance, :mother_name, :parish, :christian_name,
#                     :age_of_birth, :subcity, :woreda, :house_number, :special_place,
#                     :phone, :leving, :work_status, :email, :member_year, :spiritual_education,
#                     :rank, :education_status, :work, :student, :career, :marital_status
#                 )
#             """
#         try:
#             cursor.execute(query, form_data)
#             conn.commit()
#             flash("Member saved successfully.", "success")
#         except Exception as e:
#             flash(str(e), "danger")

#     # Delete record
#     delete_id = request.args.get('delete')
#     if delete_id:
#         try:
#             cursor.execute("DELETE FROM member_registration  WHERE id = :id", {'id': delete_id})
#             conn.commit()
#             flash("Member deleted.", "info")
#         except Exception as e:
#             flash(str(e), "danger")

#     # Fetch last 10 records
#     cursor.execute("SELECT * FROM (SELECT * FROM member_registration  ORDER BY id DESC) WHERE ROWNUM <= 10")
#     members = cursor.fetchall()
#     cursor.close()
#     conn.close()

#     return render_template("manage_members.html", members=members)

# @app.route('/manage_members', methods=['GET', 'POST'])
# def manage_members():
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     member_data = {}

#     if request.method == 'POST':
#         # Create or Update
#         form_data = request.form.to_dict()
#         member_id = form_data.get('id')

#         if member_id:
#             query = """
#                 UPDATE member_registration SET full_name=:full_name, father_of_repentance=:father_of_repentance,
#                 mother_name=:mother_name, parish=:parish, christian_name=:christian_name,
#                 age_of_birth=:age_of_birth, subcity=:subcity, woreda=:woreda, house_number=:house_number,
#                 special_place=:special_place, phone=:phone, leving=:leving, work_status=:work_status,
#                 email=:email, member_year=:member_year, spiritual_education=:spiritual_education,
#                 rank=:rank, education_status=:education_status, work=:work, student=:student,
#                 career=:career, marital_status=:marital_status
#                 WHERE id=:id
#             """
#         else:
#             query = """
#                 INSERT INTO member_registration (
#                     full_name, father_of_repentance, mother_name, parish, christian_name,
#                     age_of_birth, subcity, woreda, house_number, special_place,
#                     phone, leving, work_status, email, member_year, spiritual_education,
#                     rank, education_status, work, student, career, marital_status
#                 ) VALUES (
#                     :full_name, :father_of_repentance, :mother_name, :parish, :christian_name,
#                     :age_of_birth, :subcity, :woreda, :house_number, :special_place,
#                     :phone, :leving, :work_status, :email, :member_year, :spiritual_education,
#                     :rank, :education_status, :work, :student, :career, :marital_status
#                 )
#             """

#         try:
#             cursor.execute(query, form_data)
#             conn.commit()
#             flash("Member saved successfully.", "success")
#         except Exception as e:
#             flash(str(e), "danger")

#     # DELETE logic
#     delete_id = request.args.get('delete')
#     if delete_id:
#         try:
#             cursor.execute("DELETE FROM member_registration WHERE id = :id", {'id': delete_id})
#             conn.commit()
#             flash("Member deleted.", "info")
#         except Exception as e:
#             flash(str(e), "danger")

#     # EDIT logic
#     edit_id = request.args.get('edit')
#     if edit_id:
#         cursor.execute("SELECT * FROM member_registration WHERE id = :id", {'id': edit_id})
#         member_data = cursor.fetchone()

#     # Fetch last 10
#     cursor.execute("SELECT * FROM (SELECT * FROM member_registration ORDER BY id DESC) WHERE ROWNUM <= 10")
#     members = cursor.fetchall()
#     cursor.close()
#     conn.close()

#     return render_template("manage_members.html", members=members, member_data=member_data)
# @app.route('/manage_members', methods=['GET', 'POST'])
# def manage_members():
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     member_data = {}

#     if request.method == 'POST':
#         form_data = request.form.to_dict()
#         member_id = form_data.get('id')

#         if member_id:  # UPDATE
#             query = """
#                 UPDATE member_registration SET
#                     full_name=:full_name,
#                     father_of_repentance=:father_of_repentance,
#                     mother_name=:mother_name,
#                     parish=:parish,
#                     christian_name=:christian_name,
#                     age_of_birth=:age_of_birth,
#                     subcity=:subcity,
#                     woreda=:woreda,
#                     house_number=:house_number,
#                     special_place=:special_place,
#                     phone=:phone,
#                     leving=:leving,
#                     work_status=:work_status,
#                     email=:email,
#                     member_year=:member_year,
#                     spiritual_education=:spiritual_education,
#                     rank=:rank,
#                     education_status=:education_status,
#                     work=:work,
#                     student=:student,
#                     career=:career,
#                     marital_status=:marital_status
#                 WHERE id=:id
#             """
#         else:  # INSERT
#             query = """
#                 INSERT INTO member_registration (
#                     full_name, father_of_repentance, mother_name, parish, christian_name,
#                     age_of_birth, subcity, woreda, house_number, special_place,
#                     phone, leving, work_status, email, member_year, spiritual_education,
#                     rank, education_status, work, student, career, marital_status
#                 ) VALUES (
#                     :full_name, :father_of_repentance, :mother_name, :parish, :christian_name,
#                     :age_of_birth, :subcity, :woreda, :house_number, :special_place,
#                     :phone, :leving, :work_status, :email, :member_year, :spiritual_education,
#                     :rank, :education_status, :work, :student, :career, :marital_status
#                 )
#             """

#         try:
#             cursor.execute(query, form_data)
#             conn.commit()
#             flash("Member saved successfully.", "success")
#             return redirect(url_for('manage_members'))
#         except Exception as e:
#             flash(f"Error: {str(e)}", "danger")

#     # Handle delete
#     delete_id = request.args.get('delete')
#     if delete_id:
#         try:
#             cursor.execute("DELETE FROM member_registration WHERE id = :id", {'id': delete_id})
#             conn.commit()
#             flash("Member deleted.", "info")
#             return redirect(url_for('manage_members'))
#         except Exception as e:
#             flash(f"Error deleting member: {str(e)}", "danger")

#     # Handle edit (load member data)
#     edit_id = request.args.get('edit')
#     if edit_id:
#         cursor.execute("SELECT * FROM member_registration WHERE id = :id", {'id': edit_id})
#         member_data = cursor.fetchone()
#         # Convert to dict if cursor returns tuple (depends on cursor configuration)
#         if member_data:
#             col_names = [desc[0].lower() for desc in cursor.description]
#             member_data = dict(zip(col_names, member_data))

#     # Fetch last 10 records
#     cursor.execute("""
#         SELECT * FROM (
#             SELECT * FROM member_registration ORDER BY id DESC
#         ) WHERE ROWNUM <= 10
#     """)
#     members = cursor.fetchall()

#     # Convert members to dicts for easier template usage
#     col_names = [desc[0].lower() for desc in cursor.description]
#     members = [dict(zip(col_names, row)) for row in members]

#     cursor.close()
#     conn.close()

#     return render_template("manage_members.html", members=members, member_data=member_data)

# @app.route('/manage_members', methods=['GET', 'POST'])
# def manage_members():
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     member_data = {}

#     if request.method == 'POST':
#         form_data = request.form.to_dict()

#         # Fix the education key to match DB column
#         form_data['education'] = form_data.get('spiritual_education')
#         if 'spiritual_education' in form_data:
#             del form_data['spiritual_education']

#         member_id = form_data.get('id')

#         if member_id:  # UPDATE
#             query = """
#                 UPDATE member_registration SET
#                     full_name=:full_name,
#                     father_of_repentance=:father_of_repentance,
#                     mother_name=:mother_name,
#                     parish=:parish,
#                     christian_name=:christian_name,
#                     age_of_birth=:age_of_birth,
#                     subcity=:subcity,
#                     woreda=:woreda,
#                     house_number=:house_number,
#                     special_place=:special_place,
#                     phone=:phone,
#                     leving=:leving,
#                     work_status=:work_status,
#                     email=:email,
#                     member_year=:member_year,
#                     education=:education,
#                     rank=:rank,
#                     education_status=:education_status,
#                     work=:work,
#                     student=:student,
#                     career=:career,
#                     marital_status=:marital_status
#                 WHERE id=:id
#             """
#         else:  # INSERT
#             query = """
#                 INSERT INTO member_registration (
#                     full_name, father_of_repentance, mother_name, parish, christian_name,
#                     age_of_birth, subcity, woreda, house_number, special_place,
#                     phone, leving, work_status, email, member_year, education,
#                     rank, education_status, work, student, career, marital_status
#                 ) VALUES (
#                     :full_name, :father_of_repentance, :mother_name, :parish, :christian_name,
#                     :age_of_birth, :subcity, :woreda, :house_number, :special_place,
#                     :phone, :leving, :work_status, :email, :member_year, :education,
#                     :rank, :education_status, :work, :student, :career, :marital_status
#                 )
#             """

#         try:
#             cursor.execute(query, form_data)
#             conn.commit()
#             flash("Member saved successfully.", "success")
#             return redirect(url_for('manage_members'))
#         except Exception as e:
#             flash(f"Error: {str(e)}", "danger")

#     # Handle delete
#     delete_id = request.args.get('delete')
#     if delete_id:
#         try:
#             cursor.execute("DELETE FROM member_registration WHERE id = :id", {'id': delete_id})
#             conn.commit()
#             flash("Member deleted.", "info")
#             return redirect(url_for('manage_members'))
#         except Exception as e:
#             flash(f"Error deleting member: {str(e)}", "danger")

#     # Handle edit (load member data)
#     edit_id = request.args.get('edit')
#     if edit_id:
#         cursor.execute("SELECT * FROM member_registration WHERE id = :id", {'id': edit_id})
#         member_data = cursor.fetchone()
#         if member_data:
#             col_names = [desc[0].lower() for desc in cursor.description]
#             member_data = dict(zip(col_names, member_data))

#     # Fetch last 10 records
#     cursor.execute("""
#         SELECT * FROM (
#             SELECT * FROM member_registration ORDER BY id DESC
#         ) WHERE ROWNUM <= 10
#     """)
#     members = cursor.fetchall()

#     col_names = [desc[0].lower() for desc in cursor.description]
#     members = [dict(zip(col_names, row)) for row in members]

#     cursor.close()
#     conn.close()

#     return render_template("manage_members.html", members=members, member_data=member_data)
# @app.route('/manage_members', methods=['GET', 'POST'])
# def manage_members():
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     member_data = {}

#     # Handle form submission
#     if request.method == 'POST':
#         form_data = request.form.to_dict()

#         # Map frontend field to database field
#         form_data['education'] = form_data.pop('spiritual_education', None)
#         member_id = form_data.get('id')

#         # Prepare SQL query
#         if member_id:
#             query = """
#                 UPDATE member_registration SET
#                     full_name=:full_name,
#                     father_of_repentance=:father_of_repentance,
#                     mother_name=:mother_name,
#                     parish=:parish,
#                     christian_name=:christian_name,
#                     age_of_birth=:age_of_birth,
#                     subcity=:subcity,
#                     woreda=:woreda,
#                     house_number=:house_number,
#                     special_place=:special_place,
#                     phone=:phone,
#                     leving=:leving,
#                     work_status=:work_status,
#                     email=:email,
#                     member_year=:member_year,
#                     education=:education,
#                     rank=:rank,
#                     education_status=:education_status,
#                     work=:work,
#                     student=:student,
#                     career=:career,
#                     marital_status=:marital_status
#                 WHERE id=:id
#             """
#         else:
#             query = """
#                 INSERT INTO member_registration (
#                     full_name, father_of_repentance, mother_name, parish, christian_name,
#                     age_of_birth, subcity, woreda, house_number, special_place,
#                     phone, leving, work_status, email, member_year, education,
#                     rank, education_status, work, student, career, marital_status
#                 ) VALUES (
#                     :full_name, :father_of_repentance, :mother_name, :parish, :christian_name,
#                     :age_of_birth, :subcity, :woreda, :house_number, :special_place,
#                     :phone, :leving, :work_status, :email, :member_year, :education,
#                     :rank, :education_status, :work, :student, :career, :marital_status
#                 )
#             """

#         try:
#             cursor.execute(query, form_data)
#             conn.commit()
#             flash("Member saved successfully.", "success")
#             return redirect(url_for('manage_members'))
#         except Exception as e:
#             flash(f"Database Error: {e}", "danger")

#     # Handle delete request
#     delete_id = request.args.get('delete')
#     if delete_id:
#         try:
#             cursor.execute("DELETE FROM member_registration WHERE id = :id", {'id': delete_id})
#             conn.commit()
#             flash("Member deleted successfully.", "info")
#             return redirect(url_for('manage_members'))
#         except Exception as e:
#             flash(f"Error deleting member: {e}", "danger")

#     # Handle edit request
#     edit_id = request.args.get('edit')
#     if edit_id:
#         cursor.execute("SELECT * FROM member_registration WHERE id = :id", {'id': edit_id})
#         row = cursor.fetchone()
#         if row:
#             col_names = [desc[0].lower() for desc in cursor.description]
#             member_data = dict(zip(col_names, row))

#     # Fetch latest 10 members
#     cursor.execute("""
#         SELECT * FROM (
#             SELECT * FROM member_registration ORDER BY id DESC
#         ) WHERE ROWNUM <= 10
#     """)
#     members = cursor.fetchall()
#     col_names = [desc[0].lower() for desc in cursor.description]
#     members = [dict(zip(col_names, row)) for row in members]

#     cursor.close()
#     conn.close()

#     return render_template("manage_members.html", members=members, member_data=member_data)
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
                    full_name=:full_name,
                    father_of_repentance=:father_of_repentance,
                    mother_name=:mother_name,
                    parish=:parish,
                    christian_name=:christian_name,
                    age_of_birth=:age_of_birth,
                    subcity=:subcity,
                    woreda=:woreda,
                    house_number=:house_number,
                    special_place=:special_place,
                    phone=:phone,
                    leving=:leving,
                    work_status=:work_status,
                    email=:email,
                    member_year=:member_year,
                    education=:education,
                    rank=:rank,
                    education_status=:education_status,
                    work=:work,
                    student=:student,
                    career=:career,
                    marital_status=:marital_status,
                    section_name=:section_name,
                    gender=:gender
                WHERE id=:id
            """
        else:  # INSERT
            query = """
                INSERT INTO member_registration (
                    full_name, father_of_repentance, mother_name, parish, christian_name,
                    age_of_birth, subcity, woreda, house_number, special_place,
                    phone, leving, work_status, email, member_year, education,
                    rank, education_status, work, student, career, marital_status,section_name,gender
                ) VALUES (
                    :full_name, :father_of_repentance, :mother_name, :parish, :christian_name,
                    :age_of_birth, :subcity, :woreda, :house_number, :special_place,
                    :phone, :leving, :work_status, :email, :member_year, :education,
                    :rank, :education_status, :work, :student, :career, :marital_status, :section_name, :gender
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
            cursor.execute("DELETE FROM member_registration WHERE id = :id", {'id': delete_id})
            conn.commit()
            flash("Member deleted.", "info")
            return redirect(url_for('manage_members'))
        except Exception as e:
            flash(f"Error deleting member: {str(e)}", "danger")

    # EDIT
    edit_id = request.args.get('edit')
    if edit_id:
        cursor.execute("SELECT * FROM member_registration WHERE id = :id", {'id': edit_id})
        row = cursor.fetchone()
        if row:
            col_names = [desc[0].lower() for desc in cursor.description]
            member_data = dict(zip(col_names, row))

    # LAST 10
    cursor.execute("""
        SELECT * FROM (
            SELECT * FROM member_registration ORDER BY id DESC
        ) WHERE ROWNUM <= 10
    """)
    rows = cursor.fetchall()
    col_names = [desc[0].lower() for desc in cursor.description]
    members = [dict(zip(col_names, row)) for row in rows]

    cursor.close()
    conn.close()

    return render_template("manage_members.html", members=members, member_data=member_data)


# @app.route('/attendance', methods=['GET', 'POST'])
# def attendance():
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     attendance_data = {}

#     if request.method == 'POST':
#         form_data = request.form.to_dict()
#         attendance_id = form_data.get('id')
        
#         # Clean up
#         if not attendance_id:
#             form_data.pop('id', None)
        
#         # Ensure day_name is valid
#         form_data['day_name'] = form_data.get('day_name', '').capitalize()

#         if attendance_id:  # Update
#             query = """
#                 UPDATE attendance SET
#                     member_id = :member_id,
#                     attendance_date = TO_DATE(:attendance_date, 'YYYY-MM-DD'),
#                     present_status = :present_status,
#                     day_name = :day_name,
#                     remarks = :remarks
#                 WHERE id = :id
#             """
#         else:  # Insert
#             query = """
#                 INSERT INTO attendance (
#                     member_id, attendance_date, present_status, day_name, remarks
#                 ) VALUES (
#                     :member_id, TO_DATE(:attendance_date, 'YYYY-MM-DD'), :present_status, :day_name, :remarks
#                 )
#             """

#         try:
#             cursor.execute(query, form_data)
#             conn.commit()
#             flash("Attendance saved successfully.", "success")
#             return redirect(url_for('attendance'))
#         except Exception as e:
#             flash(f"Database Error: {str(e)}", "danger")

#     # DELETE
#     delete_id = request.args.get('delete')
#     if delete_id:
#         try:
#             cursor.execute("DELETE FROM attendance WHERE id = :id", {'id': delete_id})
#             conn.commit()
#             flash("Attendance deleted.", "info")
#             return redirect(url_for('attendance'))
#         except Exception as e:
#             flash(f"Error deleting attendance: {str(e)}", "danger")

#     # EDIT
#     edit_id = request.args.get('edit')
#     if edit_id:
#         cursor.execute("SELECT * FROM attendance WHERE id = :id", {'id': edit_id})
#         row = cursor.fetchone()
#         if row:
#             col_names = [desc[0].lower() for desc in cursor.description]
#             attendance_data = dict(zip(col_names, row))

#     # FETCH latest 20 entries with member name
#     cursor.execute("""
#         SELECT a.*, m.full_name
#         FROM (
#             SELECT * FROM attendance ORDER BY id DESC
#         ) a
#         JOIN member_registration m ON a.member_id = m.id
#         WHERE ROWNUM <= 20
#     """)
#     rows = cursor.fetchall()
#     col_names = [desc[0].lower() for desc in cursor.description]
#     attendances = [dict(zip(col_names, row)) for row in rows]

#     # Member dropdown list
#     cursor.execute("SELECT id, full_name FROM member_registration ORDER BY full_name")
#     members = cursor.fetchall()

#     cursor.close()
#     conn.close()

#     return render_template("attendance.html", attendances=attendances, attendance_data=attendance_data, members=members)


# def get_recent_weekend_dates(weeks=10):
#     today = date.today()
#     weekend_dates = []

#     # We'll look back enough days to get last 10 Saturdays and Sundays
#     days_back = weeks * 7

#     for i in range(days_back, -1, -1):  # from older to today
#         day = today - timedelta(days=i)
#         if day.weekday() in (5, 6):  # 5=Saturday, 6=Sunday
#             weekend_dates.append(day.strftime('%Y-%m-%d'))
#     return weekend_dates

# # Inside your attendance() route
# dates = get_recent_weekend_dates(10)

# @app.route('/attendance', methods=['GET', 'POST'])
# def attendance():
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     # Fetch members with their sections
#     cursor.execute("""
#         SELECT id AS member_id, full_name, section_name
#         FROM member_registration
#         ORDER BY section_name, full_name
#     """)
#     rows = cursor.fetchall()

#     # Group members by section name
#     sections = defaultdict(list)
#     for member_id, full_name, section_name in rows:
#         sections[section_name].append({'member_id': member_id, 'full_name': full_name})

#     # Convert defaultdict to list of dicts for template
#     sections = [{'name': sec, 'members': mems} for sec, mems in sections.items()]

#     # Generate a list of dates for attendance (last 7 days as example)
#     today = date.today()
#     dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
#     dates.reverse()  # oldest first

#     if request.method == 'POST':
#         # Process attendance submission
#         # Form data keys like: attendance_{member_id}_{date} = "Present" or "Absent"
#         form_data = request.form.to_dict()
#         try:
#             for section in sections:
#                 for member in section['members']:
#                     member_id = str(member['member_id'])
#                     for att_date in dates:
#                         key = f'attendance_{member_id}_{att_date}'
#                         status = form_data.get(key)
#                         if status:
#                             # Insert or update attendance record
#                             cursor.execute("""
#                                 MERGE INTO attendance a
#                                 USING (SELECT :member_id AS member_id, TO_DATE(:attendance_date, 'YYYY-MM-DD') AS attendance_date FROM dual) src
#                                 ON (a.member_id = src.member_id AND a.attendance_date = src.attendance_date)
#                                 WHEN MATCHED THEN
#                                   UPDATE SET present_status = :present_status, day_name = TO_CHAR(src.attendance_date, 'Day'), remarks = NULL
#                                 WHEN NOT MATCHED THEN
#                                   INSERT (id, member_id, attendance_date, present_status, day_name, remarks)
#                                   VALUES (attendance_seq.NEXTVAL, :member_id, TO_DATE(:attendance_date, 'YYYY-MM-DD'), :present_status, TO_CHAR(TO_DATE(:attendance_date, 'YYYY-MM-DD'), 'Day'), NULL)
#                             """, {
#                                 'member_id': member_id,
#                                 'attendance_date': att_date,
#                                 'present_status': status
#                             })
#             conn.commit()
#             flash("Attendance saved successfully.", "success")
#         except Exception as e:
#             flash(f"Database error: {str(e)}", "danger")

#         return redirect(url_for('attendance'))

#     cursor.close()
#     conn.close()

#     return render_template('attendance.html', sections=sections, dates=dates)

# @app.route('/attendance', methods=['GET', 'POST'])
# def attendance():
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     # Fetch members with their sections
#     cursor.execute("""
#         SELECT id AS member_id, full_name, section_name
#         FROM member_registration
#         ORDER BY section_name, full_name
#     """)
#     rows = cursor.fetchall()

#     # Group members by section name
#     sections = defaultdict(list)
#     for member_id, full_name, section_name in rows:
#         sections[section_name].append({'member_id': member_id, 'full_name': full_name})

#     sections = [{'name': sec, 'members': mems} for sec, mems in sections.items()]

#     # Generate recent 10 weeks of Saturdays and Sundays (20 days)
#     dates = get_recent_weekend_dates(10)

#     if request.method == 'POST':
#         form_data = request.form.to_dict()
#         try:
#             for section in sections:
#                 for member in section['members']:
#                     member_id = str(member['member_id'])
#                     for att_date in dates:
#                         key = f'attendance_{member_id}_{att_date}'
#                         status = form_data.get(key)
#                         if status:
#                             cursor.execute("""
#                                 MERGE INTO attendance a
#                                 USING (SELECT :member_id AS member_id, TO_DATE(:attendance_date, 'YYYY-MM-DD') AS attendance_date FROM dual) src
#                                 ON (a.member_id = src.member_id AND a.attendance_date = src.attendance_date)
#                                 WHEN MATCHED THEN
#                                   UPDATE SET present_status = :present_status, day_name = TO_CHAR(src.attendance_date, 'Day'), remarks = NULL
#                                 WHEN NOT MATCHED THEN
#                                   INSERT (id, member_id, attendance_date, present_status, day_name, remarks)
#                                   VALUES (attendance_seq.NEXTVAL, :member_id, TO_DATE(:attendance_date, 'YYYY-MM-DD'), :present_status, TO_CHAR(TO_DATE(:attendance_date, 'YYYY-MM-DD'), 'Day'), NULL)
#                             """, {
#                                 'member_id': member_id,
#                                 'attendance_date': att_date,
#                                 'present_status': status
#                             })
#             conn.commit()
#             flash("Attendance saved successfully.", "success")
#         except Exception as e:
#             flash(f"Database error: {str(e)}", "danger")
#         return redirect(url_for('attendance'))

#     cursor.close()
#     conn.close()

#     return render_template('attendance.html', sections=sections, dates=dates)


# def get_recent_weekend_dates(weeks=10):
#     today = date.today()
#     weekend_dates = []
#     days_back = weeks * 7
#     for i in range(days_back, -1, -1):
#         day = today - timedelta(days=i)
#         if day.weekday() in (5, 6):  # Saturday=5, Sunday=6
#             weekend_dates.append(day.strftime('%Y-%m-%d'))
#     return weekend_dates
# from collections import defaultdict
# from datetime import date, timedelta
# from flask import request, render_template, flash, redirect, url_for

# @app.route('/attendance', methods=['GET', 'POST'])
# def attendance():
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     # Fetch members grouped by section
#     cursor.execute("""
#         SELECT id AS member_id, full_name, section_name
#         FROM member_registration
#         ORDER BY section_name, full_name
#     """)
#     rows = cursor.fetchall()

#     sections = defaultdict(list)
#     for member_id, full_name, section_name in rows:
#         sections[section_name].append({'member_id': member_id, 'full_name': full_name})

#     sections = [{'name': k, 'members': v} for k, v in sections.items()]

#     # Generate last 10 weeks weekends dates (Saturdays & Sundays)
#     dates = get_recent_weekend_dates(10)

#     if request.method == 'POST':
#         form_data = request.form.to_dict()
#         try:
#             for key, value in form_data.items():
#                 if not value or not key.startswith('attendance_'):
#                     continue

#                 # key format: attendance_{member_id}_{date}
#                 parts = key.split('_')
#                 if len(parts) < 3:
#                     continue
#                 member_id = parts[1]
#                 attendance_date = parts[2]

#                 # Clean day_name from attendance_date
#                 cursor.execute("SELECT TO_CHAR(TO_DATE(:dt, 'YYYY-MM-DD'), 'Day') FROM dual", {'dt': attendance_date})
#                 day_name = cursor.fetchone()[0].strip()

#                 # Check if attendance record exists
#                 cursor.execute("""
#                     SELECT id FROM attendance
#                     WHERE member_id = :member_id AND TRUNC(attendance_date) = TO_DATE(:attendance_date, 'YYYY-MM-DD')
#                 """, {'member_id': member_id, 'attendance_date': attendance_date})
#                 row = cursor.fetchone()

#                 if row:
#                     # Update existing
#                     cursor.execute("""
#                         UPDATE attendance SET present_status = :status, day_name = :day_name
#                         WHERE id = :id
#                     """, {'status': value, 'day_name': day_name, 'id': row[0]})
#                 else:
#                     # Insert new
#                     # Get next ID - assuming you have a sequence named attendance_seq
#                     cursor.execute("SELECT attendance_seq.NEXTVAL FROM dual")
#                     new_id = cursor.fetchone()[0]

#                     cursor.execute("""
#                         INSERT INTO attendance (id, member_id, attendance_date, present_status, day_name)
#                         VALUES (:id, :member_id, TO_DATE(:attendance_date, 'YYYY-MM-DD'), :status, :day_name)
#                     """, {
#                         'id': new_id,
#                         'member_id': member_id,
#                         'attendance_date': attendance_date,
#                         'status': value,
#                         'day_name': day_name
#                     })

#             conn.commit()
#             flash("Attendance saved successfully.", "success")
#             return redirect(url_for('attendance'))

#         except Exception as e:
#             conn.rollback()
#             flash(f"Database error: {e}", "danger")

#     cursor.close()
#     conn.close()

#     return render_template('attendance.html', sections=sections, dates=dates)


# def get_recent_weekend_dates(weeks=10):
#     today = date.today()
#     weekend_dates = []
#     days_back = weeks * 7
#     for i in range(days_back, -1, -1):
#         day = today - timedelta(days=i)
#         if day.weekday() in (5, 6):  # Saturday=5, Sunday=6
#             weekend_dates.append(day.strftime('%Y-%m-%d'))
#     return weekend_dates
# def get_last_10_weeks_weekends():
#     today = date.today()
#     dates = []
#     # Collect Saturdays and Sundays for last 10 weeks
#     # We go back 70 days to be safe, collect only weekend days
#     days_back = 70
#     for i in range(days_back):
#         day = today - timedelta(days=i)
#         if day.weekday() in (5, 6):  # 5=Saturday, 6=Sunday
#             dates.append(day.strftime('%Y-%m-%d'))
#             if len(dates) >= 20:  # 10 Saturdays + 10 Sundays = 20 days total
#                 break
#     dates.sort()  # ascending order
#     return dates

# @app.route('/attendance', methods=['GET', 'POST'])
# def attendance():
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     # Step 1: Fetch members grouped by section
#     cursor.execute("""
#         SELECT id, full_name, section_name 
#         FROM member_registration 
#         ORDER BY section_name, full_name
#     """)
#     members_rows = cursor.fetchall()

#     # Organize members by section
#     sections = {}
#     for member_id, full_name, section_name in members_rows:
#         if section_name not in sections:
#             sections[section_name] = []
#         sections[section_name].append({'member_id': member_id, 'full_name': full_name})
#     sections_list = [{'name': k, 'members': v} for k, v in sections.items()]

#     # Step 2: Generate dates for last 10 weeks Saturdays and Sundays
#     dates = get_last_10_weeks_weekends()

#     if request.method == 'POST':
#         form_data = request.form.to_dict()
#         try:
#             # We'll insert or update attendance for each member/date combo found in form
#             for key, value in form_data.items():
#                 # Keys are like attendance_123_2025-06-07
#                 if not key.startswith('attendance_'):
#                     continue
#                 if value == '':
#                     continue  # skip empty

#                 _, member_id_str, att_date_str = key.split('_', 2)
#                 member_id = int(member_id_str)
#                 attendance_date = att_date_str
#                 present_status = value
#                 day_name = date.fromisoformat(attendance_date).strftime('%A')
#                 remarks = ''  # can add a remarks field if you want

#                 # Check if record exists for member_id & attendance_date
#                 cursor.execute("""
#                     SELECT id FROM attendance 
#                     WHERE member_id = :member_id AND TRUNC(attendance_date) = TO_DATE(:attendance_date, 'YYYY-MM-DD')
#                 """, {'member_id': member_id, 'attendance_date': attendance_date})
#                 row = cursor.fetchone()

#                 if row:
#                     # Update existing
#                     cursor.execute("""
#                         UPDATE attendance SET
#                             present_status = :present_status,
#                             day_name = :day_name,
#                             remarks = :remarks
#                         WHERE id = :id
#                     """, {'present_status': present_status, 'day_name': day_name, 'remarks': remarks, 'id': row[0]})
#                 else:
#                     # Insert new
#                     cursor.execute("""
#                         INSERT INTO attendance (
#                             member_id, attendance_date, present_status, day_name, remarks
#                         ) VALUES (
#                             :member_id, TO_DATE(:attendance_date, 'YYYY-MM-DD'), :present_status, :day_name, :remarks
#                         )
#                     """, {'member_id': member_id, 'attendance_date': attendance_date, 'present_status': present_status, 'day_name': day_name, 'remarks': remarks})
#             conn.commit()
#             flash("Attendance saved successfully.", "success")
#         except Exception as e:
#             conn.rollback()
#             flash(f"Error saving attendance: {e}", "danger")

#         return redirect(url_for('attendance'))

#     # Step 3: Fetch existing attendance data for displayed members/dates
#     member_ids = [m['member_id'] for section in sections_list for m in section['members']]
#     attendance_data = {}
#     if member_ids:
#         # Format for SQL IN clause
#         format_ids = ",".join(str(id) for id in member_ids)
#         format_dates = ",".join(f"TO_DATE('{d}', 'YYYY-MM-DD')" for d in dates)

#         query = f"""
#             SELECT member_id, TO_CHAR(attendance_date, 'YYYY-MM-DD') AS att_date, present_status
#             FROM attendance
#             WHERE member_id IN ({format_ids})
#               AND TRUNC(attendance_date) IN ({format_dates})
#         """
#         cursor.execute(query)
#         rows = cursor.fetchall()
#         attendance_data = {f"{r[0]}_{r[1]}": r[2] for r in rows}

#     cursor.close()
#     conn.close()

#     return render_template('attendance.html', sections=sections_list, dates=dates, attendance_data=attendance_data)


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
                    WHERE member_id = :member_id AND TRUNC(attendance_date) = TO_DATE(:attendance_date, 'YYYY-MM-DD')
                """, {'member_id': member_id, 'attendance_date': attendance_date})
                row = cursor.fetchone()

                if row:
                    cursor.execute("""
                        UPDATE attendance SET
                            present_status = :present_status,
                            day_name = :day_name,
                            remarks = :remarks
                        WHERE id = :id
                    """, {'present_status': present_status, 'day_name': day_name, 'remarks': remarks, 'id': row[0]})
                else:
                    cursor.execute("""
                        INSERT INTO attendance (
                            member_id, attendance_date, present_status, day_name, remarks
                        ) VALUES (
                            :member_id, TO_DATE(:attendance_date, 'YYYY-MM-DD'), :present_status, :day_name, :remarks
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
            SELECT id, full_name FROM member_registration WHERE section_name = :section ORDER BY full_name
        """, {'section': selected_section})
        members_rows = cursor.fetchall()
        members = [{'member_id': m[0], 'full_name': m[1]} for m in members_rows]

        # Dates for attendance
        dates = get_last_10_weeks_weekends()

        if members:
            member_ids = [m['member_id'] for m in members]
            format_ids = ",".join(str(id) for id in member_ids)
            format_dates = ",".join(f"TO_DATE('{d}', 'YYYY-MM-DD')" for d in dates)

            query = f"""
                SELECT member_id, TO_CHAR(attendance_date, 'YYYY-MM-DD') AS att_date, present_status
                FROM attendance
                WHERE member_id IN ({format_ids})
                  AND TRUNC(attendance_date) IN ({format_dates})
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










# @app.route('/bulk-payments', methods=['GET', 'POST'])
# def bulk_payments():
#     if request.method == 'POST':
#         try:
#             batch_size = int(request.form.get('batch_size', 100))
#             max_retries = int(request.form.get('max_retries', 3))
            
#             conn = get_db_connection()
#             cursor = conn.cursor()
            
#             # Call the stored procedure
#             cursor.callproc('process_bulk_payments', [batch_size, max_retries])
            
#             # Get batch results - convert to dictionary
#             cursor.execute("""
#                 SELECT 
#                     batch_id,
#                     TO_CHAR(start_time, 'YYYY-MM-DD HH24:MI:SS'),
#                     TO_CHAR(end_time, 'YYYY-MM-DD HH24:MI:SS'),
#                     batch_size,
#                     success_count,
#                     failure_count,
#                     status,
#                     error_message
#                 FROM payment_batch_log 
#                 WHERE batch_id = (SELECT MAX(batch_id) FROM payment_batch_log)
#             """)
            
#             # Convert tuple to dictionary
#             columns = [desc[0] for desc in cursor.description]
#             batch_data = cursor.fetchone()
#             batch_result = dict(zip(columns, batch_data)) if batch_data else None
            
#             if batch_result:
#                 flash(
#                     f"Bulk processing completed: {batch_result.get('success_count', 0)} succeeded, "
#                     f"{batch_result.get('failure_count', 0)} failed",
#                     'success'
#                 )
#                 return redirect(url_for('bulk_payment_results', batch_id=batch_result['batch_id']))
#             else:
#                 flash('No batch results found', 'warning')
#                 return redirect(request.url)
            
#         except Exception as e:
#             flash(f'Error processing bulk payments: {str(e)}', 'danger')
#             app.logger.error(f"Bulk payment error: {str(e)}", exc_info=True)
#             return redirect(request.url)
    
#     return render_template('bulk_payments.html')
# @role_required('Finance', 'Super Admin')
# def bulk_payments():
#     if request.method == 'POST':
#         try:
#             batch_size = int(request.form.get('batch_size', 100))
#             max_retries = int(request.form.get('max_retries', 3))
            
#             conn = get_db_connection()
#             cursor = conn.cursor()
            
#             cursor.callproc('process_bulk_payments', [batch_size, max_retries])
            
#             # Get batch results
#             cursor.execute("""
#                 SELECT * FROM payment_batch_log 
#                 WHERE batch_id = (SELECT MAX(batch_id) FROM payment_batch_log)
#             """)
#             batch_result = cursor.fetchone()
            
#             flash(f"Bulk processing completed: {batch_result['success_count']} succeeded, {batch_result['failure_count']} failed", 'success')
#             return redirect(url_for('bulk_payment_results', batch_id=batch_result['batch_id']))
            
#         except Exception as e:
#             flash(f'Error processing bulk payments: {str(e)}', 'danger')
#             app.logger.error(f"Bulk payment error: {str(e)}", exc_info=True)
#             return redirect(request.url)
    
#     return render_template('bulk_payments.html')

# @app.route('/bulk-payments/results/<batch_id>')
# @role_required('Finance', 'Super Admin')
# def bulk_payment_results(batch_id):
#     conn = get_db_connection()
#     cursor = conn.cursor()
    
#     try:
#         # Get batch summary
#         cursor.execute("""
#             SELECT * FROM payment_batch_log
#             WHERE batch_id = :batch_id
#         """, {'batch_id': batch_id})
        
#         batch = cursor.fetchone()
        
#         if not batch:
#             flash('Batch not found', 'danger')
#             return redirect(url_for('bulk_payments'))
        
#         # Get failed payments with pagination
#         page = request.args.get('page', 1, type=int)
#         per_page = 50
#         offset = (page - 1) * per_page
        
#         cursor.execute("""
#             SELECT * FROM PAYMENT_FAILED_LOG
#             WHERE batch_id = :batch_id
#             ORDER BY failure_time DESC
#             OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY"""
#             , {
#             'batch_id': batch_id,
#             'offset': offset,
#             'per_page': per_page
#         })
        
#         failures = cursor.fetchall()
        
#         # Get total count for pagination
#         cursor.execute("""
#             SELECT COUNT(*) FROM PAYMENT_FAILED_LOG
#             WHERE batch_id = :batch_id
#         """, {'batch_id': batch_id})
        
#         total = cursor.fetchone()[0]
#         pages = ceil(total / per_page)
        
#         return render_template(
#             'bulk_payment_results.html',
#             batch=batch,
#             failures=failures,
#             page=page,
#             pages=pages,
#             total=total
#         )
        
#     except Exception as e:
#         flash(f'Error retrieving results: {str(e)}', 'danger')
#         return redirect(url_for('bulk_payments'))
#     finally:
#         cursor.close()
#         conn.close()


# @app.route('/bulk-payments/results/<batch_id>')
# @role_required('Finance', 'Super Admin')
# def bulk_payment_results(batch_id):
#     conn = get_db_connection()
#     cursor = conn.cursor()
    
#     try:
#         # Get batch summary - convert to dictionary
#         cursor.execute("""
#             SELECT 
#                 batch_id,
#                 TO_CHAR(start_time, 'YYYY-MM-DD HH24:MI:SS') as start_time,
#                 TO_CHAR(end_time, 'YYYY-MM-DD HH24:MI:SS') as end_time,
#                 batch_size,
#                 success_count,
#                 failure_count,
#                 status,
#                 error_message
#             FROM payment_batch_log
#             WHERE batch_id = :batch_id
#         """, {'batch_id': batch_id})
        
#         # Convert to dictionary
#         columns = [desc[0] for desc in cursor.description]
#         batch_data = cursor.fetchone()
#         batch = dict(zip(columns, batch_data)) if batch_data else None
        
#         if not batch:
#             flash('Batch not found', 'danger')
#             return redirect(url_for('bulk_payments'))
        
#         # Get failed payments with pagination
#         page = request.args.get('page', 1, type=int)
#         per_page = 50
#         offset = (page - 1) * per_page
        
#         cursor.execute("""
#             SELECT 
#                 banktxnref,
#                 billkey,
#                 customerkey,
#                 amount,
#                 error_message,
#                 TO_CHAR(failure_time, 'YYYY-MM-DD HH24:MI:SS') as failure_time
#             FROM payment_failed_log
#             WHERE batch_id = :batch_id
#             ORDER BY failure_time DESC
#             OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY
#         """, {
#             'batch_id': batch_id,
#             'offset': offset,
#             'per_page': per_page
#         })
        
#         # Convert each row to dictionary
#         failures = []
#         columns = [desc[0] for desc in cursor.description]
#         for row in cursor.fetchall():
#             failures.append(dict(zip(columns, row)))
        
#         # Get total count for pagination
#         cursor.execute("""
#             SELECT COUNT(*) FROM payment_failed_log
#             WHERE batch_id = :batch_id
#         """, {'batch_id': batch_id})
        
#         total = cursor.fetchone()[0]
#         pages = ceil(total / per_page)
        
#         return render_template(
#             'bulk_payment_results.html',
#             batch=batch,
#             failures=failures,
#             page=page,
#             pages=pages,
#             total=total
#         )
        
#     except Exception as e:
#         flash(f'Error retrieving results: {str(e)}', 'danger')
#         return redirect(url_for('bulk_payments'))
#     finally:
#         cursor.close()
#         conn.close()
# @app.template_filter('datetimeformat')
# def datetimeformat(value):
#     return value.strftime('%Y-%m-%d %H:%M:%S') if value else ''
# @app.template_filter('durationformat')
# def durationformat(value):
#     seconds = int(value.total_seconds())
#     hours, remainder = divmod(seconds, 3600)
#     minutes, seconds = divmod(remainder, 60)
#     return f"{hours}h {minutes}m {seconds}s"
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

@app.route('/bulk_payment_results/<batch_id>')
def bulk_payment_results(batch_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    with conn.cursor() as cursor:
        cursor.execute("""
        SELECT 
            batch_id, 
            start_time, 
            end_time, 
            batch_size, 
            success_count, 
            failure_count, 
            status, 
            error_message
        FROM payment_batch_log
        WHERE batch_id = :batch_id
    """, {'batch_id': batch_id})
        row = cursor.fetchone()
        if not row:
            return render_template("not_found.html", message="Batch ID not found.")

    # Don't convert again — it's already datetime
        batch = {
            'batch_id': row[0],
            'start_time': row[1],
            'end_time': row[2],
            'batch_size': row[3],
            'success_count': row[4],
            'failure_count': row[5],
            'status': row[6],
            'error_message': row[7]
        }


    # with conn.cursor() as cursor:
    #     # Fetch batch summary
    #     cursor.execute("""
    #         SELECT 
    #             batch_id, 
    #             start_time, 
    #             end_time, 
    #             batch_size, 
    #             success_count, 
    #             failure_count, 
    #             status, 
    #             error_message
    #         FROM payment_batch_log
    #         WHERE batch_id = :batch_id
    #     """, {'batch_id': batch_id})
    #     row = cursor.fetchone()
    #     if not row:
    #         return render_template("not_found.html", message="Batch ID not found.")

    #     batch = {
    #         'batch_id': row[0],
    #         'start_time': datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S'),
    #         'end_time': datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S'),
    #         'batch_size': row[3],
    #         'success_count': row[4],
    #         'failure_count': row[5],
    #         'status': row[6],
    #         'error_message': row[7]
    #     }

    #     # Fetch failures with pagination
        cursor.execute("""
            SELECT COUNT(*) FROM payment_failed_log WHERE batch_id = :batch_id
        """, {'batch_id': batch_id})
        total = cursor.fetchone()[0]
        pages = math.ceil(total / per_page)

        cursor.execute("""
            SELECT banktxnref, billkey, customerkey, amount, error_message, failure_time
            FROM (
                SELECT a.*, ROWNUM rnum FROM (
                    SELECT * FROM payment_failed_log 
                    WHERE batch_id = :batch_id 
                    ORDER BY failure_time DESC
                ) a WHERE ROWNUM <= :end_row
            ) WHERE rnum > :start_row
        """, {
            'batch_id': batch_id,
            'start_row': offset,
            'end_row': offset + per_page
        })
        rows = cursor.fetchall()
        failures = []
        for r in rows:
            failures.append({
                'banktxnref': r[0],
                'billkey': r[1],
                'customerkey': r[2],
                'amount': r[3],
                'error_message': r[4],
                'failure_time': r[5]
            })

    return render_template(
        'bulk_payment_results.html',
        batch=batch,
        failures=failures,
        total=total,
        page=page,
        pages=pages
    )
def get_failures_for_batch(batch_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT banktxnref, billkey, customerkey, amount, error_message, failure_time
        FROM payment_failed_log
        WHERE batch_id = :batch_id
        ORDER BY failure_time DESC
    """, {'batch_id': batch_id})
    rows = cursor.fetchall()
    failures = []
    for r in rows:
        failures.append({
            'banktxnref': r[0],
            'billkey': r[1],
            'customerkey': r[2],
            'amount': r[3],
            'error_message': r[4],
            'failure_time': r[5]
        })
    cursor.close()
    conn.close()
    return failures

@app.route('/export-failures/<batch_id>')
def export_bulk_payment_failures(batch_id):
    failures = get_failures_for_batch(batch_id)

    if not failures:
        return Response("No failures found for this batch.", mimetype='text/plain')

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Bank Txn Ref', 'Bill Key', 'Customer Key', 'Amount', 'Error Message', 'Failure Time'])

    for f in failures:
        writer.writerow([
            f['banktxnref'],
            f['billkey'] or 'N/A',
            f['customerkey'] or 'N/A',
            f['amount'],
            f['error_message'],
            f['failure_time'].strftime('%Y-%m-%d %H:%M:%S') if f['failure_time'] else ''
        ])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment; filename=failures_batch_{batch_id}.csv"}
    )



    
@app.route('/upload_vat', methods=['GET', 'POST'])
@login_required
# @login_required
@role_required('Super Admin') 
def upload_vat():
    if request.method == 'POST':
        file = request.files['file']
        if not file or not file.filename.endswith('.csv'):
            flash("Please upload a valid CSV file.", "danger")
            return redirect('/upload_vat')

        connection = get_db_connection()
        cursor = connection.cursor()

        duplicate_bill_keys = set()  # Using set for faster lookups
        inserted_count = 0
        csv_bill_keys = set()
        rows = []

        # Define the expected column order
        COLUMNS = [
            'BILL_KEY','VAT_AMOUNT'
        ]

        try:
            # Process the file in memory for faster access
            file_content = file.stream.read().decode('utf-8').splitlines()
            reader = csv.reader(file_content)
            
            # Skip header if exists
            next(reader, None)

            # Single pass processing with immediate duplicate checking
            for row in reader:
                if not row:
                    continue

                try:
                    row_dict = dict(zip(COLUMNS, row))
                    bill_key = row_dict['BILL_KEY']

                    # Check for duplicates in CSV first
                    if bill_key in csv_bill_keys:
                        duplicate_bill_keys.add(bill_key)
                        continue

                    csv_bill_keys.add(bill_key)
                    rows.append(row_dict)
                except (IndexError, KeyError) as e:
                    app.logger.warning(f"Skipping malformed row: {row}. Error: {str(e)}")
                    continue

            # Bulk check for existing keys in database
            if rows:
                # Use batches to avoid too many parameters (Oracle has a limit)
                batch_size = 1000
                existing_keys = set()
                
                for i in range(0, len(csv_bill_keys), batch_size):
                    batch = list(csv_bill_keys)[i:i + batch_size]
                    placeholders = ', '.join([':key'+str(i) for i in range(len(batch))])
                    params = {'key'+str(i): key for i, key in enumerate(batch)}
                    
                    cursor.execute(f"SELECT BILL_KEY FROM bill_vat WHERE BILL_KEY IN ({placeholders})", params)
                    existing_keys.update(row[0] for row in cursor.fetchall())

                # Filter and prepare for insert
                unique_rows = []
                for row in rows:
                    if row['BILL_KEY'] in existing_keys:
                        duplicate_bill_keys.add(row['BILL_KEY'])
                    else:
                        unique_rows.append(row)

                # Bulk insert in batches
                if unique_rows:
                    insert_sql = """
                        INSERT INTO bill_vat (
                            BILL_KEY, VAT_AMOUNT
                        ) VALUES (
                            :BILL_KEY, :VAT_AMOUNT
                        )
                    """
                    
                    # Insert in batches to avoid memory issues
                    for i in range(0, len(unique_rows), batch_size):
                        batch = unique_rows[i:i + batch_size]
                        cursor.executemany(insert_sql, batch)
                    
                    inserted_count = len(unique_rows)
                    connection.commit()
                    flash(f"Successfully uploaded {inserted_count} bills!", "success")
                else:
                    flash("No unique bill data to upload.", "warning")

            # Prepare duplicate message
            if duplicate_bill_keys:
                dup_count = len(duplicate_bill_keys)
                sample_duplicates = ', '.join(list(duplicate_bill_keys)[:5])
                if dup_count > 5:
                    sample_duplicates += f" and {dup_count-5} more"
                flash(f"Skipped {dup_count} duplicate bill keys (sample: {sample_duplicates})", "info")

        except Exception as e:
            connection.rollback()
            flash(f"Error uploading bill data: {str(e)}", "danger")
            app.logger.error(f"Error in upload_bill: {str(e)}", exc_info=True)
        
        finally:
            cursor.close()
            connection.close()

        return redirect('/upload_vat')

    return render_template('upload_vat.html')


def initialize_reconciliation_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if tables exist first
        cursor.execute("""
        BEGIN
            EXECUTE IMMEDIATE 'CREATE TABLE reconciliation_uploads (
                upload_id VARCHAR2(50) PRIMARY KEY,
                filename VARCHAR2(255) NOT NULL,
                total_records NUMBER NOT NULL,
                matched_records NUMBER DEFAULT 0,
                unmatched_records NUMBER DEFAULT 0,
                duplicate_records NUMBER DEFAULT 0,
                uploaded_by VARCHAR2(50) NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR2(20) DEFAULT ''PROCESSING''
            )';
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE != -955 THEN -- table already exists
                    RAISE;
                END IF;
        END;
        """)
        
        cursor.execute("""
        BEGIN
            EXECUTE IMMEDIATE 'CREATE TABLE reconciliation_results (
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                upload_id VARCHAR2(50) NOT NULL,
                billkey VARCHAR2(50) ,
                banktxnref VARCHAR2(100) NOT NULL,
                status VARCHAR2(20) NOT NULL,
                matched_at TIMESTAMP,
                uploaded_by VARCHAR2(50) NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )';
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE != -955 THEN -- table already exists
                    RAISE;
                END IF;
        END;
        """)
        
        cursor.execute("""
        BEGIN
            EXECUTE IMMEDIATE 'ALTER TABLE reconciliation_results ADD CONSTRAINT uk_reconciliation_unique UNIQUE ( banktxnref)';
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE != -2261 THEN -- constraint already exists
                    RAISE;
                END IF;
        END;
        """)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error initializing reconciliation tables: {str(e)}")
    finally:
        cursor.close()
        conn.close()

# Call this at app startup
initialize_reconciliation_tables()


@app.route('/reconciliation', methods=['GET', 'POST'])
@role_required('Finance', 'Super Admin')  # Only authorized roles can access
def reconciliation():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
            
        if not file.filename.lower().endswith('.csv'):
            flash('Only CSV files are allowed', 'danger')
            return redirect(request.url)
            
        try:
            # Process the file
            result = process_reconciliation_file(file, session['payroll_number'])
            session['reconciliation_warnings'] = result.get('warnings', [])

            
            # Prepare summary message
            msg = (
                f"Reconciliation completed. "
                f"Total: {result['total']}, "
                f"Matched: {result['matched']}, "
                f"Unmatched: {result['unmatched']}, "
                f"Duplicates: {result['duplicates']}"
            )
            flash(msg, 'success')
            
            return redirect(url_for('reconciliation_results', upload_id=result['upload_id']))
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
            app.logger.error(f"Reconciliation error: {str(e)}", exc_info=True)
            return redirect(request.url)
    
    # GET request - show upload form
    return render_template('reconciliation.html')


def process_reconciliation_file(file, uploaded_by):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Generate unique upload ID
        upload_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)

        stream = io.TextIOWrapper(file.stream, encoding='utf-8')
        reader = csv.DictReader(stream)

        total = matched = unmatched = duplicates = 0
        warnings = []
        seen_keys = set()  # To detect duplicates in the same upload
        batch = []

        # Insert initial tracking record
        cursor.execute("""
            INSERT INTO reconciliation_uploads (
                upload_id, filename, total_records, uploaded_by
            ) VALUES (
                :upload_id, :filename, :total, :uploaded_by
            )
        """, {
            'upload_id': upload_id,
            'filename': filename,
            'total': 0,
            'uploaded_by': uploaded_by
        })

        for row in reader:
            total += 1
            # billkey = row.get('billkey', '').strip()
            banktxnref = row.get('BANKTXNREF', '').strip()

            if  not banktxnref:
                continue  # Skip invalid rows

            unique_key = f"{banktxnref}"
            if unique_key in seen_keys:
                duplicates += 1
                status = 'DUPLICATE'
                warnings.append(f"Duplicate in file:  banktxnref={banktxnref}")
            else:
                seen_keys.add(unique_key)
                # Check if already in DB
                cursor.execute("""
                    SELECT 1 FROM reconciliation_results 
                    WHERE banktxnref = :banktxnref
                """, { 'banktxnref': banktxnref})
                if cursor.fetchone():
                    duplicates += 1
                    status = 'DUPLICATE'
                    
                    # warnings.append(f"Duplicate in database:  banktxnref={banktxnref}")
                    MAX_WARNINGS = 20
                    if len(warnings) < MAX_WARNINGS:
                        warnings.append(f"Duplicate in database:  banktxnref={banktxnref}")
                    else:
                        if len(warnings) == MAX_WARNINGS:
                            warnings.append("... too many duplicates, showing only first 20.")

                else:
                    # Check if matched in payment table
                    cursor.execute("""
                        SELECT 1 FROM payment 
                        WHERE  BANKTXNREF = :banktxnref
                    """, { 'banktxnref': banktxnref})
                    if cursor.fetchone():
                        matched += 1
                        status = 'MATCHED'
                    else:
                        unmatched += 1
                        status = 'UNMATCHED'

            # batch.append({
            #     'upload_id': upload_id,
            #     'billkey': billkey,
            #     'banktxnref': banktxnref,
            #     'status': status,
            #     'uploaded_by': uploaded_by,
            #     'matched_at': datetime.now() if status == 'MATCHED' else None
            # })
            if status != 'DUPLICATE':
                batch.append({
        'upload_id': upload_id,
        'banktxnref': banktxnref,
        'status': status,
        'uploaded_by': uploaded_by,
        'matched_at': datetime.now() if status == 'MATCHED' else None
    })

            if len(batch) >= 100:
                cursor.executemany("""
                    INSERT INTO reconciliation_results (
                        upload_id,  banktxnref, status, 
                        matched_at, uploaded_by
                    ) VALUES (
                        :upload_id,  :banktxnref, :status,
                        :matched_at, :uploaded_by
                    )
                """, batch)
                batch = []

        if batch:
            cursor.executemany("""
                INSERT INTO reconciliation_results (
                    upload_id,  banktxnref, status, 
                    matched_at, uploaded_by
                ) VALUES (
                    :upload_id,  :banktxnref, :status,
                    :matched_at, :uploaded_by
                )
            """, batch)

        # Update summary
        cursor.execute("""
            UPDATE reconciliation_uploads
            SET 
                total_records = :total,
                matched_records = :matched,
                unmatched_records = :unmatched,
                duplicate_records = :duplicates,
                status = 'COMPLETED'
            WHERE upload_id = :upload_id
        """, {
            'total': total,
            'matched': matched,
            'unmatched': unmatched,
            'duplicates': duplicates,
            'upload_id': upload_id
        })

        conn.commit()

        return {
            'upload_id': upload_id,
            'total': total,
            'matched': matched,
            'unmatched': unmatched,
            'duplicates': duplicates,
            'warnings': warnings  # Show this in the frontend
        }

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()



@app.route('/reconciliation/results/<upload_id>')
@role_required('Finance', 'Super Admin')
def reconciliation_results(upload_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    warnings = session.pop('reconciliation_warnings', [])  # Remove after reading
    
    try:
        # Get upload summary
        cursor.execute("""
            SELECT * FROM reconciliation_uploads
            WHERE upload_id = :upload_id
        """, {'upload_id': upload_id})
        
        upload = cursor.fetchone()
        
        if not upload:
            flash('Upload not found', 'danger')
            return redirect(url_for('reconciliation'))
        
        # Get results with pagination
        page = request.args.get('page', 1, type=int)
        per_page = 50
        offset = (page - 1) * per_page
        
        cursor.execute("""
            SELECT  banktxnref, status, 
                   matched_at, uploaded_by
            FROM reconciliation_results
            WHERE upload_id = :upload_id
            ORDER BY status
            OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY
        """, {
            'upload_id': upload_id,
            'offset': offset,
            'per_page': per_page
        })
        
        results = cursor.fetchall()
        
        # Get total count for pagination
        cursor.execute("""
            SELECT COUNT(*) FROM reconciliation_results
            WHERE upload_id = :upload_id
        """, {'upload_id': upload_id})
        
        total = cursor.fetchone()[0]
        pages = ceil(total / per_page)
        
        # Convert results to a list of dictionaries for easier template access
        formatted_results = []
        for row in results:
            # formatted_results.append({
            #     'banktxnref': row[1],
            #     'status': row[2],
            #     'matched_at': row[3],
            #     'uploaded_by': row[4]
        #     })
            formatted_results.append({
    'banktxnref': row[0],
    'status': row[1],
    'matched_at': row[2],
    'uploaded_by': row[3]
})

        
        return render_template(
            'reconciliation_results.html',
            upload={
                'id': upload[0],
                'filename': upload[1],
                'total': upload[2],
                'matched': upload[3],
                'unmatched': upload[4],
                'duplicates': upload[5],
                'uploaded_by': upload[6],
                'uploaded_at': upload[7],
                'status': upload[8]
            },
            results=formatted_results,
            page=page,
            pages=pages,
            total=total, warnings=warnings, upload_id=upload_id
        )
        
    except Exception as e:
        flash(f'Error retrieving results: {str(e)}', 'danger')
        return redirect(url_for('reconciliation'))
    finally:
        cursor.close()
        conn.close()

@app.route('/reconciliation/export/<upload_id>')
@role_required('Finance', 'Super Admin')
def export_reconciliation(upload_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get upload info
        cursor.execute("""
            SELECT filename FROM reconciliation_uploads
            WHERE upload_id = :upload_id
        """, {'upload_id': upload_id})
        
        upload = cursor.fetchone()
        
        if not upload:
            flash('Upload not found', 'danger')
            return redirect(url_for('reconciliation'))
        
        # Get all results
        cursor.execute("""
            SELECT  banktxnref, status, 
                   TO_CHAR(matched_at, 'YYYY-MM-DD HH24:MI:SS') as matched_at
            FROM reconciliation_results
            WHERE upload_id = :upload_id
            ORDER BY status
        """, {'upload_id': upload_id})
        
        results = cursor.fetchall()
        
        # Create CSV in memory
        si = io.StringIO()
        cw = csv.writer(si)
        
        # Write header
        cw.writerow([ 'BANKTXNREF', 'STATUS', 'MATCHED_AT'])
        
        # Write data
        for row in results:
            cw.writerow(row)
        
        # Prepare response
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=reconciliation_{upload_id}.csv"
        output.headers["Content-type"] = "text/csv"
        
        return output
        
    except Exception as e:
        flash(f'Error exporting results: {str(e)}', 'danger')
        return redirect(url_for('reconciliation_results', upload_id=upload_id))
    finally:
        cursor.close()
        conn.close()
# csrf = CSRFProtect(app)
# app.config['WTF_CSRF_ENABLED'] = False  # Only for testing!

# @app.before_request
# def check_csrf():
#     if request.method == "POST":
#         token = session.pop('_csrf_token', None)
#         if not token or token != request.form.get('csrf_token'):
#         #    bort(403)
#             print("invalid Token")

# def generate_csrf_token():
#     if '_csrf_token' not in session:
#         session['_csrf_token'] = str(uuid.uuid4())
#     return session['_csrf_token']

# app.jinja_env.globals['csrf_token'] = generate_csrf_token
# @app.route('/payment_management', methods=['GET', 'POST'])
# @role_required('Customer Service', 'Super Admin')
# def payment_management():
#     if request.method == 'POST':
#         # Verify CSRF token
#         if not verify_csrf(request.form.get('csrf_token')):
#             flash('Invalid CSRF token', 'danger')
#             return redirect(url_for('payment_management'))

#         action = request.form.get('action')
#         if not action:
#             flash('No action specified', 'danger')
#             return redirect(url_for('payment_management'))

#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         try:
#             if action == 'mark_paid':
#                 # Validate and get form data
#                 bill_key = request.form.get('bill_key')
#                 customer_key = request.form.get('customer_key')
#                 amount = request.form.get('amount')
#                 bank_txn_ref = request.form.get('bank_txn_ref')
#                 payment_channel = request.form.get('payment_channel')
                
#                 if not all([bill_key, customer_key, amount, bank_txn_ref, payment_channel]):
#                     flash('All fields are required', 'danger')
#                     return redirect(url_for('payment_management'))

#                 # Check if bill exists
#                 cursor.execute("SELECT 1 FROM BILL WHERE BILLKEY = :bill_key", {'bill_key': bill_key})
#                 if not cursor.fetchone():
#                     flash('Bill not found', 'danger')
#                     return redirect(url_for('payment_management'))

#                 # Check if payment already exists
#                 cursor.execute("SELECT 1 FROM PAYMENT WHERE BILLKEY = :bill_key", {'bill_key': bill_key})
#                 if cursor.fetchone():
#                     flash('Payment already exists for this bill', 'warning')
#                     return redirect(url_for('payment_management'))

#                 # Insert payment
#                 payment_key = str(uuid.uuid4())
#                 cursor.execute("""
#                     INSERT INTO PAYMENT (
#                         PAYMENTKEY, BILLKEY, CUSTOMERKEY, AMOUNT, BANKTXNREF,
#                         PAYMENTCHANNEL, PAYMENTDATE, REQUESTID, CHANNEL, PAYMENTCOMPLETEDAT
#                     ) VALUES (
#                         :payment_key, :bill_key, :customer_key, :amount, :bank_txn_ref,
#                         :payment_channel, TO_CHAR(SYSDATE, 'YYYY-MM-DD'), :request_id, :channel, SYSTIMESTAMP
#                     )
#                 """, {
#                     'payment_key': payment_key,
#                     'bill_key': bill_key,
#                     'customer_key': customer_key,
#                     'amount': amount,
#                     'bank_txn_ref': bank_txn_ref,
#                     'payment_channel': payment_channel,
#                     'request_id': str(uuid.uuid4())[:20],
#                     'channel': 'MANUAL_CORRECTION'
#                 })

#                 # Log correction
#                 cursor.execute("""
#                     INSERT INTO PAYMENT_CORRECTIONS (
#                         CORRECTION_ID, BILLKEY, ACTION, PERFORMED_BY, PERFORMED_AT, NOTES
#                     ) VALUES (
#                         payment_corrections_seq.NEXTVAL, :bill_key, 'MARKED_PAID', :user, SYSTIMESTAMP, 
#                         'Manually marked as paid'
#                     )
#                 """, {
#                     'bill_key': bill_key,
#                     'user': session['payroll_number']
#                 })

#                 conn.commit()
#                 flash('Payment successfully recorded', 'success')

#             elif action == 'reverse_payment':
#                 bill_key = request.form.get('bill_key')
#                 if not bill_key:
#                     flash('Bill key is required', 'danger')
#                     return redirect(url_for('payment_management'))

#                 # Get payment to reverse
#                 cursor.execute("""
#                     SELECT PAYMENTKEY FROM PAYMENT 
#                     WHERE BILLKEY = :bill_key
#                 """, {'bill_key': bill_key})
#                 payment = cursor.fetchone()
                
#                 if not payment:
#                     flash('No payment found for this bill', 'danger')
#                     return redirect(url_for('payment_management'))

#                 # Delete payment
#                 cursor.execute("""
#                     DELETE FROM PAYMENT 
#                     WHERE PAYMENTKEY = :payment_key
#                 """, {'payment_key': payment[0]})

#                 # Log correction
#                 cursor.execute("""
#                     INSERT INTO PAYMENT_CORRECTIONS (
#                         CORRECTION_ID, BILLKEY, ACTION, PERFORMED_BY, PERFORMED_AT, NOTES
#                     ) VALUES (
#                         payment_corrections_seq.NEXTVAL, :bill_key, 'REVERSED', :user, SYSTIMESTAMP, 
#                         'Payment reversed'
#                     )
#                 """, {
#                     'bill_key': bill_key,
#                     'user': session['payroll_number']
#                 })

#                 conn.commit()
#                 flash('Payment successfully reversed', 'success')

#             else:
#                 flash('Invalid action', 'danger')

#         except Exception as e:
#             conn.rollback()
#             flash(f'Error processing request: {str(e)}', 'danger')
#             app.logger.error(f"Payment management error: {str(e)}", exc_info=True)
#         finally:
#             cursor.close()
#             conn.close()
        
#         return redirect(url_for('payment_management'))

#     # GET request handling remains the same...
#     search_query = request.args.get('search', '')
#     page = request.args.get('page', 1, type=int)
#     per_page = 20
    
#     conn = get_db_connection()
#     cursor = conn.cursor()
    
#     try:
#         # Get bills
#         query = """
#             SELECT b.BILLKEY, b.CUSTOMERKEY, b.CUSTOMERNAME, b.CUSTOMERBRANCH, 
#                    b.TOTALBILLAMOUNT, b.REASON,
#                    CASE WHEN p.BILLKEY IS NOT NULL THEN 'PAID' ELSE 'UNPAID' END as payment_status
#             FROM BILL b
#             LEFT JOIN PAYMENT p ON b.BILLKEY = p.BILLKEY
#             WHERE 1=1
#         """
        
#         params = {}
        
#         if search_query:
#             query += " AND (b.BILLKEY LIKE :search OR b.CUSTOMERKEY LIKE :search OR b.CUSTOMERNAME LIKE :search)"
#             params['search'] = f'%{search_query}%'
        
#         query += " ORDER BY b.BILLKEY"
        
#         # Pagination
#         cursor.execute(f"SELECT COUNT(*) FROM ({query})", params)
#         total = cursor.fetchone()[0]
#         pages = ceil(total / per_page)
#         offset = (page - 1) * per_page
        
#         cursor.execute(f"""
#             {query}
#             OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY
#         """, {**params, 'offset': offset, 'per_page': per_page})
        
#         bills = cursor.fetchall()
        
#         # Get recent corrections
#         cursor.execute("""
#             SELECT b.BILLKEY, b.CUSTOMERNAME, pc.ACTION, pc.PERFORMED_BY, 
#                    TO_CHAR(pc.PERFORMED_AT, 'YYYY-MM-DD HH24:MI:SS'), pc.NOTES
#             FROM PAYMENT_CORRECTIONS pc
#             JOIN BILL b ON pc.BILLKEY = b.BILLKEY
#             ORDER BY pc.PERFORMED_AT DESC
#             FETCH FIRST 10 ROWS ONLY
#         """)
        
#         recent_corrections = cursor.fetchall()
        
#     except Exception as e:
#         flash(f'Error retrieving data: {str(e)}', 'danger')
#         bills = []
#         recent_corrections = []
#     finally:
#         cursor.close()
#         conn.close()
    
#     return render_template(
#         'payment_management.html',
#         bills=bills,
#         recent_corrections=recent_corrections,
#         search_query=search_query,
#         page=page,
#         pages=pages,
#         total=total
#     )

# @app.route('/payment_management', methods=['GET', 'POST'])
# @role_required('Customer Service', 'Super Admin')
# def payment_management():
#     if request.method == 'POST':
#         action = request.form.get('action')
#         if not action:
#             flash('No action specified', 'danger')
#             return redirect(url_for('payment_management'))

#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         try:
#             if action == 'mark_paid':
#                 # Validate and get form data
#                 bill_key = request.form.get('bill_key')
#                 customer_key = request.form.get('customer_key')
#                 amount = request.form.get('amount')
#                 bank_txn_ref = request.form.get('bank_txn_ref')
#                 payment_channel = request.form.get('payment_channel')
                
#                 if not all([bill_key, customer_key, amount, bank_txn_ref, payment_channel]):
#                     flash('All fields are required', 'danger')
#                     return redirect(url_for('payment_management'))

#                 # Check if bill exists
#                 cursor.execute("SELECT 1 FROM BILL WHERE BILLKEY = :bill_key", {'bill_key': bill_key})
#                 if not cursor.fetchone():
#                     flash('Bill not found', 'danger')
#                     return redirect(url_for('payment_management'))

#                 # Check if payment already exists
#                 cursor.execute("SELECT 1 FROM PAYMENT WHERE BILLKEY = :bill_key", {'bill_key': bill_key})
#                 if cursor.fetchone():
#                     flash('Payment already exists for this bill', 'warning')
#                     return redirect(url_for('payment_management'))

#                 # Insert payment
#                 payment_key = str(uuid.uuid4())
#                 request_id = str(uuid.uuid4())[:20]
#                 cursor.execute("""
#                     INSERT INTO PAYMENT (
#                         PAYMENTKEY, BILLKEY, CUSTOMERKEY, AMOUNT, BANKTXNREF,
#                         PAYMENTCHANNEL, PAYMENTDATE, REQUESTID, CHANNEL, PAYMENTCOMPLETEDAT
#                     ) VALUES (
#                         :payment_key, :bill_key, :customer_key, :amount, :bank_txn_ref,
#                         :payment_channel, TO_CHAR(SYSDATE, 'YYYY-MM-DD'), :request_id, :channel, SYSTIMESTAMP
#                     )
#                 """, {
#                     'payment_key': payment_key,
#                     'bill_key': bill_key,
#                     'customer_key': customer_key,
#                     'amount': amount,
#                     'bank_txn_ref': bank_txn_ref,
#                     'payment_channel': payment_channel,
#                     'request_id': request_id,
#                     'channel': 'MANUAL_CORRECTION'
#                 })

#                 # Log correction
#                 cursor.execute("""
#                     INSERT INTO PAYMENT_CORRECTIONS (
#                         CORRECTION_ID, BILLKEY, ACTION, PERFORMED_BY, PERFORMED_AT, NOTES
#                     ) VALUES (
#                         payment_corrections_seq.NEXTVAL, :bill_key, 'MARKED_PAID', :user, SYSTIMESTAMP, 
#                         'Manually marked as paid'
#                     )
#                 """, {
#                     'bill_key': bill_key,
#                     'user': session['payroll_number']
#                 })

#                 conn.commit()
#                 flash('Payment successfully recorded', 'success')

#             elif action == 'reverse_payment':
#                 bill_key = request.form.get('bill_key')
#                 if not bill_key:
#                     flash('Bill key is required', 'danger')
#                     return redirect(url_for('payment_management'))

#                 # Get payment to reverse
#                 cursor.execute("""
#                     SELECT PAYMENTKEY FROM PAYMENT 
#                     WHERE BILLKEY = :bill_key
#                 """, {'bill_key': bill_key})
#                 payment = cursor.fetchone()
                
#                 if not payment:
#                     flash('No payment found for this bill', 'danger')
#                     return redirect(url_for('payment_management'))

#                 # Delete payment
#                 cursor.execute("""
#                     DELETE FROM PAYMENT 
#                     WHERE PAYMENTKEY = :payment_key
#                 """, {'payment_key': payment[0]})

#                 # Log correction
#                 cursor.execute("""
#                     INSERT INTO PAYMENT_CORRECTIONS (
#                         CORRECTION_ID, BILLKEY, ACTION, PERFORMED_BY, PERFORMED_AT, NOTES
#                     ) VALUES (
#                         payment_corrections_seq.NEXTVAL, :bill_key, 'REVERSED', :user, SYSTIMESTAMP, 
#                         'Payment reversed'
#                     )
#                 """, {
#                     'bill_key': bill_key,
#                     'user': session['payroll_number']
#                 })

#                 conn.commit()
#                 flash('Payment successfully reversed', 'success')

#             else:
#                 flash('Invalid action', 'danger')

#         except Exception as e:
#             conn.rollback()
#             flash(f'Error processing request: {str(e)}', 'danger')
#             app.logger.error(f"Payment management error: {str(e)}", exc_info=True)
#         finally:
#             cursor.close()
#             conn.close()
        
#         return redirect(url_for('payment_management'))

#     # GET request handling
#     search_query = request.args.get('search', '')
#     page = request.args.get('page', 1, type=int)
#     per_page = 20
    
#     conn = get_db_connection()
#     cursor = conn.cursor()
    
#     try:
#         query = """
#             SELECT b.BILLKEY, b.CUSTOMERKEY, b.CUSTOMERNAME, b.CUSTOMERBRANCH, 
#                    b.TOTALBILLAMOUNT, b.REASON,
#                    CASE WHEN p.BILLKEY IS NOT NULL THEN 'PAID' ELSE 'UNPAID' END as payment_status
#             FROM BILL b
#             LEFT JOIN PAYMENT p ON b.BILLKEY = p.BILLKEY
#             WHERE 1=1
#         """
        
#         params = {}
#         if search_query:
#             query += " AND (b.BILLKEY LIKE :search OR b.CUSTOMERKEY LIKE :search OR b.CUSTOMERNAME LIKE :search)"
#             params['search'] = f'%{search_query}%'
        
#         query += " ORDER BY b.BILLKEY"
        
#         cursor.execute(f"SELECT COUNT(*) FROM ({query})", params)
#         total = cursor.fetchone()[0]
#         pages = ceil(total / per_page)
#         offset = (page - 1) * per_page
        
#         cursor.execute(f"""
#             {query}
#             OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY
#         """, {**params, 'offset': offset, 'per_page': per_page})
        
#         bills = cursor.fetchall()
        
#         cursor.execute("""
#             SELECT b.BILLKEY, b.CUSTOMERNAME, pc.ACTION, pc.PERFORMED_BY, 
#                    TO_CHAR(pc.PERFORMED_AT, 'YYYY-MM-DD HH24:MI:SS'), pc.NOTES
#             FROM PAYMENT_CORRECTIONS pc
#             JOIN BILL b ON pc.BILLKEY = b.BILLKEY
#             ORDER BY pc.PERFORMED_AT DESC
#             FETCH FIRST 10 ROWS ONLY
#         """)
        
#         recent_corrections = cursor.fetchall()
        
#     except Exception as e:
#         flash(f'Error retrieving data: {str(e)}', 'danger')
#         bills = []
#         recent_corrections = []
#     finally:
#         cursor.close()
#         conn.close()
    
#     return render_template(
#         'payment_management.html',
#         bills=bills,
#         recent_corrections=recent_corrections,
#         search_query=search_query,
#         page=page,
#         pages=pages,
#         total=total
#     )

@app.route('/payment_management', methods=['GET', 'POST'])
@login_required
@role_required('Customer Service', 'Super Admin')
def payment_management():
    def insert_payment(cursor, data):
        # payment_key = str(uuid.uuid4())
        request_id = str(uuid.uuid4())[:20]
    #  request_id = str(uuid.uuid4())[:20]

    # Fetch the next value from the PAYMENT_KEY_SEQ sequence
        cursor.execute("SELECT AAWSA_API.PAYMENT_KEY_SEQ.NEXTVAL FROM DUAL")
        payment_key = cursor.fetchone()[0]  # Get the sequence value for PAYMENTKEY

        cursor.execute("""
    INSERT INTO PAYMENT (
        PAYMENTKEY, BILLKEY, CUSTOMERKEY, AMOUNT, BANKTXNREF,
        PAYMENTCHANNEL, PAYMENTDATE, REQUESTID, CHANNEL,
        PAYMENTCOMPLETEDAT, CORRECTOR, REVERSED
    ) VALUES (
        :payment_key, :bill_key, :customer_key, :amount, :bank_txn_ref,
        :payment_channel, TO_CHAR(SYSDATE, 'YYYY-MM-DD'), :request_id, 'MANUAL_CORRECTION',
        SYSTIMESTAMP, :corrector, 0
    )
""", {
    'payment_key': payment_key,
    'bill_key': data['bill_key'],
    'customer_key': data['customer_key'],
    'amount': data['amount'],
    'bank_txn_ref': data['bank_txn_ref'],
    'payment_channel': data['payment_channel'],
    'request_id': request_id,
    'corrector': session.get('payroll_number', 'UNKNOWN')
})
    def log_correction(cursor, bill_key, action, notes):
        # Ensure that the session variable is available
            if 'payroll_number' not in session:
                raise ValueError("Payroll number not found in session")

            # Get the payroll number from the session
            performed_by = session['payroll_number']
            cursor.execute("""
    INSERT INTO PAYMENT_CORRECTIONS (
        BILLKEY, ACTION, PERFORMED_BY, PERFORMED_AT, NOTES
    ) VALUES (
        :bill_key, :action, :performed_by, SYSTIMESTAMP, :notes
    )
""", {
    'bill_key': bill_key,
    'action': action,
    'performed_by': performed_by,
    'notes': notes
})
        

    if request.method == 'POST':
        action = request.form.get('action')
        if not action:
            flash('No action specified', 'danger')
            return redirect(url_for('payment_management'))

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if action == 'mark_paid':
                form_data = {
                    'bill_key': request.form.get('bill_key'),
                    'customer_key': request.form.get('customer_key'),
                    'amount': request.form.get('amount'),
                    'bank_txn_ref': request.form.get('bank_txn_ref'),
                    'payment_channel': request.form.get('payment_channel')
                }

                if not all(form_data.values()):
                    flash('All fields are required', 'danger')
                    return redirect(url_for('payment_management'))

                # Check bill existence
                cursor.execute("SELECT 1 FROM BILL WHERE BILLKEY = :bill_key", {'bill_key': form_data['bill_key']})
                if not cursor.fetchone():
                    flash('Bill not found', 'danger')
                    return redirect(url_for('payment_management'))

                # Check if the bill has an existing payment and if it was reversed
                cursor.execute("SELECT PAYMENTKEY, REVERSED FROM PAYMENT WHERE BILLKEY = :bill_key", {'bill_key': form_data['bill_key']})
                payment = cursor.fetchone()
                request_id = str(uuid.uuid4())[:20]
                corrector = session.get('payroll_number', 'UNKNOWN')

                if payment:
                    # If the payment is reversed, allow it to be re-marked as paid
                    if payment[1] == 1:
                        cursor.execute("""
    UPDATE PAYMENT
    SET REVERSED = 0,
        AMOUNT = :amount,
        BANKTXNREF = :bank_txn_ref,
        PAYMENTCHANNEL = :payment_channel,
        REQUESTID = :request_id,
        CORRECTOR = :corrector,
        PAYMENTCOMPLETEDAT = SYSTIMESTAMP
    WHERE PAYMENTKEY = :payment_key
""", {
    'payment_key': payment[0],
    'amount': form_data['amount'],
    'bank_txn_ref': form_data['bank_txn_ref'],
    'payment_channel': form_data['payment_channel'],
    'request_id': request_id,
    'corrector': corrector
})
                        log_correction(cursor, form_data['bill_key'], 'MARKED_PAID', 'Payment re-marked as paid after reversal')
                        conn.commit()
                        flash('Payment successfully re-marked as paid', 'success')
                    else:
                        flash('Payment already exists for this bill and is not in reversed state', 'warning')
                        return redirect(url_for('payment_management'))
                else:
                    # If no existing payment is found, insert a new payment record
                    insert_payment(cursor, form_data)
                    log_correction(cursor, form_data['bill_key'], 'MARKED_PAID', 'Manually marked as paid')
                    conn.commit()
                    flash('Payment successfully recorded', 'success')
            elif action == 'reverse_payment':
                bill_key = request.form.get('bill_key')
                if not bill_key:
                    flash('Bill key is required', 'danger')
                    return redirect(url_for('payment_management'))
                cursor.execute("SELECT PAYMENTKEY, REVERSED FROM PAYMENT WHERE BILLKEY = :bill_key", {'bill_key': bill_key})
                payment = cursor.fetchone()

                if not payment:
                    flash('No payment found for this bill', 'danger')
                    return redirect(url_for('payment_management'))

                if payment[1] == 1:
                    flash('Payment has already been reversed', 'warning')
                    return redirect(url_for('payment_management'))

                cursor.execute("""
                    UPDATE PAYMENT 
    SET REVERSED = 1,
        CORRECTOR = :corrector,
        REQUESTID = :request_id,
        PAYMENTCOMPLETEDAT = SYSTIMESTAMP
    WHERE PAYMENTKEY = :payment_key
""", {
    'payment_key': payment[0],
    'corrector': session.get('payroll_number', 'UNKNOWN'),
    'request_id': str(uuid.uuid4())[:20]})

                log_correction(cursor, bill_key, 'REVERSED', 'Payment reversed')
                conn.commit()
                flash('Payment successfully reversed', 'success')


            else:
                flash('Invalid action', 'danger')

        except Exception as e:
            conn.rollback()
            app.logger.error(f"Payment management error: {str(e)}", exc_info=True)
            flash(f'Error processing request: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('payment_management'))

    # GET method
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        base_query = """
    SELECT b.BILLKEY, b.CUSTOMERKEY, b.CUSTOMERNAME, b.CUSTOMERBRANCH, 
           b.TOTALBILLAMOUNT, b.REASON,
           CASE 
               WHEN p.BILLKEY IS NOT NULL AND p.REVERSED = 0 THEN 'PAID' 
               ELSE 'UNPAID' 
           END AS payment_status
    FROM BILL b
    LEFT JOIN PAYMENT p ON b.BILLKEY = p.BILLKEY
    WHERE 1=1
"""
#         base_query = """
#             SELECT b.BILLKEY, b.CUSTOMERKEY, b.CUSTOMERNAME, b.CUSTOMERBRANCH, 
#                    b.TOTALBILLAMOUNT, b.REASON,
#                    CASE 
#     WHEN p.BILLKEY IS NOT NULL AND p.REVERSED = 0 THEN 'PAID'
#     ELSE 'UNPAID'
# END AS payment_status
#             FROM BILL b
#             LEFT JOIN PAYMENT p ON b.BILLKEY = p.BILLKEY
#             WHERE 1=1
#         """

        params = {}

        if search_query:
            base_query += " AND (b.BILLKEY LIKE :search OR b.CUSTOMERKEY LIKE :search OR b.CUSTOMERNAME LIKE :search)"
            params['search'] = f'%{search_query}%'

        total_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor.execute(total_query, params)
        total = cursor.fetchone()[0]
        pages = ceil(total / per_page)

        cursor.execute(f"""
            {base_query}
            ORDER BY b.BILLKEY
            OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY
        """, {**params, 'offset': offset, 'per_page': per_page})

        bills = cursor.fetchall()

        # Recent corrections
        cursor.execute("""
            SELECT b.BILLKEY, b.CUSTOMERNAME, pc.ACTION, pc.PERFORMED_BY, 
                   TO_CHAR(pc.PERFORMED_AT, 'YYYY-MM-DD HH24:MI:SS'), pc.NOTES
            FROM PAYMENT_CORRECTIONS pc
            JOIN BILL b ON pc.BILLKEY = b.BILLKEY
            ORDER BY pc.PERFORMED_AT DESC
            FETCH FIRST 10 ROWS ONLY
        """)
        recent_corrections = cursor.fetchall()

    except Exception as e:
        flash(f'Error retrieving data: {str(e)}', 'danger')
        bills, recent_corrections, total, pages = [], [], 0, 1
    finally:
        cursor.close()
        conn.close()

    return render_template(
        'payment_management.html',
        bills=bills,
        recent_corrections=recent_corrections,
        search_query=search_query,
        page=page,
        pages=pages,
        total=total
    )

# @app.route('/payment_management', methods=['GET', 'POST'])
# @role_required('Customer Service', 'Super Admin')
# def payment_management():
#     if request.method == 'POST':
#         action = request.form.get('action')
#         bill_key = request.form.get('bill_key')
#         customer_key = request.form.get('customer_key')
#         amount = request.form.get('amount')
#         bank_txn_ref = request.form.get('bank_txn_ref')
#         payment_channel = request.form.get('payment_channel')
        
#         if not bill_key:
#             flash('Bill key is required', 'danger')
#             return redirect(url_for('payment_management'))
            
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         try:
#             if action == 'mark_paid':
#                 # Validate required fields
#                 if not all([customer_key, amount, bank_txn_ref, payment_channel]):
#                     flash('All fields are required to mark a payment', 'danger')
#                     return redirect(url_for('payment_management'))
                
#                 # Check if bill exists
#                 cursor.execute("SELECT 1 FROM BILL WHERE BILLKEY = :bill_key", {'bill_key': bill_key})
#                 if not cursor.fetchone():
#                     flash('Bill not found in system', 'danger')
#                     return redirect(url_for('payment_management'))
                
#                 # Check if payment already exists
#                 cursor.execute("SELECT 1 FROM PAYMENT WHERE BILLKEY = :bill_key", {'bill_key': bill_key})
#                 if cursor.fetchone():
#                     flash('Payment already exists for this bill', 'warning')
#                     return redirect(url_for('payment_management'))
                
#                 # Insert payment record
#                 payment_key = str(uuid.uuid4())
#                 cursor.execute("""
#                     INSERT INTO PAYMENT (
#                         PAYMENTKEY, BILLKEY, CUSTOMERKEY, AMOUNT, BANKTXNREF,
#                         PAYMENTCHANNEL, PAYMENTDATE, REQUESTID, CHANNEL, PAYMENTCOMPLETEDAT
#                     ) VALUES (
#                         :payment_key, :bill_key, :customer_key, :amount, :bank_txn_ref,
#                         :payment_channel, TO_CHAR(SYSDATE, 'YYYY-MM-DD'), :request_id, :channel, SYSTIMESTAMP
#                     )
#                 """, {
#                     'payment_key': payment_key,
#                     'bill_key': bill_key,
#                     'customer_key': customer_key,
#                     'amount': amount,
#                     'bank_txn_ref': bank_txn_ref,
#                     'payment_channel': payment_channel,
#                     'request_id': str(uuid.uuid4())[:20],
#                     'channel': 'MANUAL_CORRECTION'
#                 })
                
#                 # Log the action
#                 cursor.execute("""
#                     INSERT INTO PAYMENT_CORRECTIONS (
#                         CORRECTION_ID, BILLKEY, ACTION, PERFORMED_BY, PERFORMED_AT, NOTES
#                     ) VALUES (
#                         payment_corrections_seq.NEXTVAL, :bill_key, 'MARKED_PAID', :user, SYSTIMESTAMP, 
#                         'Manually marked as paid by customer service'
#                     )
#                 """, {
#                     'bill_key': bill_key,
#                     'user': session['payroll_number']
#                 })
                
#                 conn.commit()
#                 flash('Payment successfully recorded', 'success')
                
#             elif action == 'reverse_payment':
#                 # Check if payment exists
#                 cursor.execute("""
#                     SELECT PAYMENTKEY FROM PAYMENT 
#                     WHERE BILLKEY = :bill_key
#                 """, {'bill_key': bill_key})
                
#                 payment = cursor.fetchone()
#                 if not payment:
#                     flash('No payment found for this bill', 'danger')
#                     return redirect(url_for('payment_management'))
                
#                 # Delete the payment
#                 cursor.execute("""
#                     DELETE FROM PAYMENT 
#                     WHERE PAYMENTKEY = :payment_key
#                 """, {'payment_key': payment[0]})
                
#                 # Log the action
#                 cursor.execute("""
#                     INSERT INTO PAYMENT_CORRECTIONS (
#                         CORRECTION_ID, BILLKEY, ACTION, PERFORMED_BY, PERFORMED_AT, NOTES
#                     ) VALUES (
#                         payment_corrections_seq.NEXTVAL, :bill_key, 'REVERSED', :user, SYSTIMESTAMP, 
#                         'Payment reversed by customer service'
#                     )
#                 """, {
#                     'bill_key': bill_key,
#                     'user': session['payroll_number']
#                 })
                
#                 conn.commit()
#                 flash('Payment successfully reversed', 'success')
                
#             else:
#                 flash('Invalid action', 'danger')
                
#         except Exception as e:
#             conn.rollback()
#             flash(f'Error processing request: {str(e)}', 'danger')
#             app.logger.error(f"Payment management error: {str(e)}", exc_info=True)
#         finally:
#             cursor.close()
#             conn.close()
            
#         return redirect(url_for('payment_management'))
    
#     # GET request - show the interface
#     search_query = request.args.get('search', '')
#     page = request.args.get('page', 1, type=int)
#     per_page = 20
    
#     conn = get_db_connection()
#     cursor = conn.cursor()
    
#     try:
#         # Get bills that might need attention
#         query = """
#             SELECT b.BILLKEY, b.CUSTOMERKEY, b.CUSTOMERNAME, b.CUSTOMERBRANCH, 
#                    b.TOTALBILLAMOUNT, b.REASON,
#                    CASE WHEN p.BILLKEY IS NOT NULL THEN 'PAID' ELSE 'UNPAID' END as payment_status
#             FROM BILL b
#             LEFT JOIN PAYMENT p ON b.BILLKEY = p.BILLKEY
#             WHERE 1=1
#         """
        
#         params = {}
        
#         if search_query:
#             query += " AND (b.BILLKEY LIKE :search OR b.CUSTOMERKEY LIKE :search OR b.CUSTOMERNAME LIKE :search)"
#             params['search'] = f'%{search_query}%'
        
#         query += " ORDER BY b.BILLKEY"
        
#         # For pagination
#         cursor.execute(f"SELECT COUNT(*) FROM ({query})", params)
#         total = cursor.fetchone()[0]
#         pages = ceil(total / per_page)
#         offset = (page - 1) * per_page
        
#         cursor.execute(f"""
#             {query}
#             OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY
#         """, {**params, 'offset': offset, 'per_page': per_page})
        
#         bills = cursor.fetchall()
        
#         # Get recent corrections for audit trail
#         cursor.execute("""
#             SELECT b.BILLKEY, b.CUSTOMERNAME, pc.ACTION, pc.PERFORMED_BY, 
#                    TO_CHAR(pc.PERFORMED_AT, 'YYYY-MM-DD HH24:MI:SS'), pc.NOTES
#             FROM PAYMENT_CORRECTIONS pc
#             JOIN BILL b ON pc.BILLKEY = b.BILLKEY
#             ORDER BY pc.PERFORMED_AT DESC
#             FETCH FIRST 10 ROWS ONLY
#         """)
        
#         recent_corrections = cursor.fetchall()
        
#     except Exception as e:
#         flash(f'Error retrieving data: {str(e)}', 'danger')
#         bills = []
#         recent_corrections = []
#     finally:
#         cursor.close()
#         conn.close()
    
#     return render_template(
#         'payment_management.html',
#         bills=bills,
#         recent_corrections=recent_corrections,
#         search_query=search_query,
#         page=page,
#         pages=pages,
#         total=total
#     )
# def verify_csrf(token):
#     """Helper function to verify CSRF token"""
#     try:
#         from flask_wtf.csrf import validate_csrf
#         validate_csrf(token)
#         return True
#     except:
#         return False


@app.route('/logout')
def logout():
    session.pop('payroll_number', None)  # Remove payroll_number from the session
    return redirect(url_for('login'))  # Redirect to the login page

if __name__ == '__main__':
    app.run(debug=True,port=5001,host="0.0.0.0")
