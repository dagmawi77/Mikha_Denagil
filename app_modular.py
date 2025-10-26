"""
Modularized Flask Application for Member and Attendance Management
Main entry point - imports from modules
"""
# Standard library imports
import csv
import io
from datetime import datetime, date, timedelta
from math import ceil

# Third-party imports
import pandas as pd
from flask import (
    Flask, render_template, request, redirect, url_for, 
    session, flash, send_file, make_response, jsonify, Response
)
from werkzeug.utils import secure_filename
import mysql.connector
from openpyxl import Workbook
from reportlab.lib.pagesizes import A3, landscape, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepInFrame
)
from reportlab.pdfgen import canvas
from fpdf import FPDF

# Local imports
from config import Config
from database import (
    get_db_connection, 
    initialize_rbac_tables, 
    initialize_default_roles_and_routes,
    test_db_connection
)
from auth import (
    login_required, 
    role_required, 
    get_authorized_routes,
    verify_password,
    hash_password
)
from utils import get_last_10_weeks_weekends, get_members

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# ========================================
# SESSION MANAGEMENT
# ========================================

@app.before_request
def make_session_permanent():
    """Make session permanent for timeout management"""
    session.permanent = True

def track_session_timeout():
    """Track and enforce session timeout"""
    if 'last_activity' in session:
        now = datetime.now()
        last_activity_str = session['last_activity']
        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            timeout_seconds = Config.SESSION_TIMEOUT_MINUTES * 60
            if (now - last_activity).total_seconds() > timeout_seconds:
                session.clear()
                flash("Session timed out due to inactivity.", "warning")
                return redirect(url_for('login'))
        except:
            pass
    session['last_activity'] = datetime.now().isoformat()

# ========================================
# CONTEXT PROCESSORS
# ========================================

@app.context_processor
def inject_navigation():
    """Inject authorized routes into all templates"""
    return dict(authorized_routes=get_authorized_routes())

# ========================================
# AUTHENTICATION ROUTES
# ========================================

@app.route('/', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'POST':
        payroll_number = request.form['payroll_number']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        
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

        if user and verify_password(user[4], password):  # user[4] is password_hash
            session['payroll_number'] = payroll_number
            session['role'] = user[-1]  # role_name is last column
            session['last_activity'] = datetime.now().isoformat()
            flash("Login successful!", "success")
            return redirect(url_for('navigation'))
        else:
            flash("Invalid credentials", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# ========================================
# DASHBOARD & NAVIGATION
# ========================================

@app.route('/navigation')
@login_required
def navigation():
    """Main navigation/dashboard page with real statistics"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    # Get total members count
    cursor.execute("SELECT COUNT(*) FROM member_registration")
    total_members = cursor.fetchone()[0] or 0
    
    # Get members by section (for cards)
    cursor.execute("""
        SELECT section_name, COUNT(*) 
        FROM member_registration 
        GROUP BY section_name
    """)
    section_counts = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Get counts for each section card
    children_count = section_counts.get('የሕፃናት ክፍል', 0)
    middle_count = section_counts.get('ማህከላዊያን ክፍል', 0)
    youth_count = section_counts.get('ወጣት ክፍል', 0)
    parent_count = section_counts.get('ወላጅ ክፍል', 0)
    
    # Get attendance statistics for current month
    cursor.execute("""
        SELECT COUNT(*) 
        FROM attendance 
        WHERE MONTH(attendance_date) = MONTH(CURDATE())
        AND YEAR(attendance_date) = YEAR(CURDATE())
    """)
    current_month_attendance = cursor.fetchone()[0] or 0
    
    # Get data for charts - Members by section
    cursor.execute("""
        SELECT section_name, COUNT(*) as count
        FROM member_registration
        GROUP BY section_name
        ORDER BY section_name
    """)
    section_data = cursor.fetchall()
    branch_labels = [row[0] for row in section_data]
    channel_amounts = [row[1] for row in section_data]
    
    # Get gender distribution by section for stacked bar chart
    cursor.execute("""
        SELECT section_name, gender, COUNT(*) as count
        FROM member_registration
        GROUP BY section_name, gender
        ORDER BY section_name, gender
    """)
    gender_data = cursor.fetchall()
    
    # Organize data for stacked chart
    sections = list(set([row[0] for row in gender_data]))
    male_data = []
    female_data = []
    
    for section in sections:
        male_count = sum([row[2] for row in gender_data if row[0] == section and row[1] in ('ወንድ', 'Male')])
        female_count = sum([row[2] for row in gender_data if row[0] == section and row[1] in ('ሴት', 'Female')])
        male_data.append(male_count)
        female_data.append(female_count)
    
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
    
    cursor.close()
    conn.close()
    
    # Current period (month/year)
    current_period = datetime.now().strftime('%B %Y')
    
    return render_template('navigation.html',
                         # Summary report table - IMPORTANT!
                         current_settled=current_settled,
                         current_delivery=[],
                         current_unsettled=[],
                         recent_sent_bills=[],
                         # Card 1: Total Members
                         current_bill_count=total_members,
                         bill_period=current_period,
                         # Card 2: ማህከላዊያን ክፍል (Middle Section)
                         current_month_total_bill_amnt=middle_count,
                         current_month_bill_amnt='ማህከላዊያን ክፍል',
                         # Card 3: የሕፃናት ክፍል (Children Section)
                         payment_count=children_count,
                         payment_month='የሕፃናት ክፍል',
                         # Card 4: ወጣት ክፍል (Youth Section)
                         payment_total_bill_amnt=youth_count,
                         payment_this_month_bill_amnt='ወጣት ክፍል',
                         # Card 5: ወላጅ ክፍል (Parent Section)
                         parent_section_count=parent_count,
                         # Additional stats
                         total_paid_amount=0,
                         total_sent_amount=0,
                         number_sent=0,
                         number_paid=0,
                         # Chart data - Members by section (pie chart)
                         channel_labels=branch_labels,
                         channel_amounts=channel_amounts,
                         # Chart data - Stacked bar (gender by section)
                         branch_labels=sections,
                         number_sent_data=male_data,
                         total_amount_sent_data=female_data,
                         outstanding_amount=[],
                         this_month_bill_amnt=[],
                         payment_data=[])

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')

@app.route('/dashboard-data')
@login_required
def dashboard_data():
    """API endpoint that returns dashboard data as JSON"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    # Get total members
    cursor.execute("SELECT COUNT(*) FROM member_registration")
    total_members = cursor.fetchone()[0] or 0
    
    # Get members by section (for cards)
    cursor.execute("""
        SELECT section_name, COUNT(*) 
        FROM member_registration 
        GROUP BY section_name
    """)
    section_counts = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Get counts for each section card
    children_count = section_counts.get('የሕፃናት ክፍል', 0)
    middle_count = section_counts.get('ማህከላዊያን ክፍል', 0)
    youth_count = section_counts.get('ወጣት ክፍል', 0)
    parent_count = section_counts.get('ወላጅ ክፍል', 0)
    
    # Get data for charts - Members by section
    cursor.execute("""
        SELECT section_name, COUNT(*) as count
        FROM member_registration
        GROUP BY section_name
        ORDER BY section_name
    """)
    section_data = cursor.fetchall()
    branch_labels = [row[0] for row in section_data]
    channel_amounts = [row[1] for row in section_data]
    
    # Get gender distribution by section for stacked bar chart
    cursor.execute("""
        SELECT section_name, gender, COUNT(*) as count
        FROM member_registration
        GROUP BY section_name, gender
        ORDER BY section_name, gender
    """)
    gender_data = cursor.fetchall()
    
    # Organize data for stacked chart
    sections = list(set([row[0] for row in gender_data]))
    male_data = []
    female_data = []
    
    for section in sections:
        male_count = sum([row[2] for row in gender_data if row[0] == section and row[1] in ('ወንድ', 'Male')])
        female_count = sum([row[2] for row in gender_data if row[0] == section and row[1] in ('ሴት', 'Female')])
        male_data.append(male_count)
        female_data.append(female_count)
    
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
    current_settled = [[col for col in row] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    # Current period (month/year)
    current_period = datetime.now().strftime('%B %Y')
    
    data = {
        'current_bill_count': total_members,
        'bill_period': current_period,
        'current_month_total_bill_amnt': middle_count,
        'current_month_bill_amnt': middle_count,
        'payment_count': children_count,
        'payment_month': 'የሕፃናት ክፍል',
        'payment_total_bill_amnt': youth_count,
        'payment_this_month_bill_amnt': 'ወጣት ክፍል',
        'parent_section_count': parent_count,
        'current_settled': current_settled,
        'current_delivery': [],
        'current_unsettled': [],
        'branch_labels': sections,
        'number_sent_data': male_data,
        'total_amount_sent_data': female_data,
        'outstanding_amount': [],
        'this_month_bill_amnt': [],
        'channel_labels': branch_labels,
        'channel_amounts': channel_amounts
    }
    
    # Debug logging
    print(f"Dashboard data - Summary report rows: {len(current_settled)}")
    if current_settled:
        print(f"First row: {current_settled[0]}")
    
    return jsonify(data)

@app.route('/admin_dashboard')
@login_required
@role_required('Super Admin')
def admin_dashboard():
    """Admin dashboard"""
    return render_template('admin_dashboard.html')

# ========================================
# MEMBER MANAGEMENT ROUTES
# ========================================

@app.route('/manage_members', methods=['GET', 'POST'])
@login_required
def manage_members():
    """Manage member registrations - CRUD operations"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
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

    # Get filters
    search = request.args.get('search', '')
    section_filter = request.args.get('section', '')
    gender_filter = request.args.get('gender', '')
    
    # Build query with filters
    query = "SELECT * FROM member_registration WHERE 1=1"
    params = []
    
    if search:
        query += " AND full_name LIKE %s"
        params.append(f'%{search}%')
    
    if section_filter:
        query += " AND section_name = %s"
        params.append(section_filter)
    
    if gender_filter:
        query += " AND gender = %s"
        params.append(gender_filter)
    
    query += " ORDER BY id DESC"
    
    cursor.execute(query, params)
    members = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("manage_members.html", 
                         members=members, 
                         member_data=member_data,
                         search=search,
                         section_filter=section_filter,
                         gender_filter=gender_filter)

@app.route('/member_report')
@login_required
def member_report():
    """Comprehensive member report with statistics and charts"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
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

@app.route('/upload_member_registration', methods=['GET', 'POST'])
@login_required
def upload_member_registration():
    """Upload member registrations from CSV file"""
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.csv'):
            flash("Please upload a valid CSV file.", "warning")
            return redirect(url_for('upload_member_registration'))

        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)

        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)

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

# ========================================
# ATTENDANCE ROUTES  
# ========================================

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    """Mark attendance for members by section"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

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

@app.route('/attendance_report', methods=['GET', 'POST'])
@login_required
def attendance_report():
    """View and export attendance reports"""
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', 'All')
    export_format = request.args.get('format', None)
    page = request.args.get('page', 1, type=int)
    per_page = Config.ITEMS_PER_PAGE
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    if request.method == 'POST':
        search_query = request.form.get('search', '')
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')

    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    # Base query for filtering
    query = """
      SELECT FULL_NAME, GENDER, CHRISTIAN_NAME, PHONE, SECTION_NAME, ATTENDANCE_DATE, PRESENT_STATUS 
      FROM MEMBER_REGISTRATION a, attendance b 
      WHERE a.id=b.member_id
    """

    params = {}

    # Add search filter
    if search_query:
        query += " AND (a.FULL_NAME LIKE %(search)s OR a.PHONE LIKE %(search)s)"
        params['search'] = f'%{search_query}%'

    # Add branch/section filter
    if selected_branch != 'All':
        query += " AND a.SECTION_NAME = %(branch)s"
        params['branch'] = selected_branch

    # Add date range filter
    if start_date and end_date:
        try:
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
            flash("Invalid date format", "danger")

    # Finalize query order
    query += " ORDER BY FULL_NAME, ATTENDANCE_DATE"

    # Execute query
    cursor.execute(query, params)
    filtered_records = cursor.fetchall()

    # Pagination logic
    total = len(filtered_records)
    pages = ceil(total / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    payments_paginated = filtered_records[start:end]

    # Export functionality
    if export_format == 'csv':
        return export_attendance_csv(filtered_records)
    elif export_format == 'pdf':
        return attendance_report_pdf(filtered_records)
    elif export_format == 'excel':
        return attendance_report_excel(filtered_records)

    # Close database connection
    cursor.close()
    conn.close()

    # Fetch branches/sections for filter dropdown
    branches = get_members()

    # Render template
    return render_template(
        'attendance_report.html',
        payments=payments_paginated,
        search_query=search_query,
        branches=branches,
        selected_branch=selected_branch,
        start_date=start_date,
        end_date=end_date,
        page=page,
        pages=pages,
        total=total
    )

# ========================================
# EXPORT FUNCTIONS
# ========================================

def export_attendance_csv(data):
    """Export attendance data to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Full Name', 'Gender', 'Christian Name', 'Phone', 'Section', 'Date', 'Status'])
    
    # Write data
    for row in data:
        writer.writerow(row)
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=attendance_report.csv'
    return response

def attendance_report_pdf(data):
    """Export attendance report to PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A3)
    elements = []
    
    # Title
    styles = getSampleStyleSheet()
    title = Paragraph("<b>Attendance Report</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))
    
    # Table data
    table_data = [['Full Name', 'Gender', 'Christian Name', 'Phone', 'Section', 'Date', 'Status']]
    for row in data:
        table_data.append(list(row))
    
    # Create table
    t = Table(table_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(t)
    doc.build(elements)
    
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, 
                     download_name='attendance_report.pdf')

def attendance_report_excel(data):
    """Export attendance report to Excel"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance Report"
    
    # Write header
    headers = ['Full Name', 'Gender', 'Christian Name', 'Phone', 'Section', 'Date', 'Status']
    ws.append(headers)
    
    # Write data
    for row in data:
        ws.append(list(row))
    
    # Create response
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return send_file(buffer, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='attendance_report.xlsx')

# ========================================
# USER MANAGEMENT ROUTES
# ========================================

@app.route('/user_management')
@login_required
@role_required('Super Admin')
def user_management():
    """Manage application users"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    cursor.execute("""
        SELECT u.user_id, u.payroll_number, u.username, u.email, u.full_name, 
               u.branch, u.is_active, u.last_login, r.role_name
        FROM aawsa_user u
        LEFT JOIN roles r ON u.role_id = r.role_id
        ORDER BY u.user_id DESC
    """)
    
    users = []
    for row in cursor.fetchall():
        users.append({
            'user_id': row[0],
            'payroll_number': row[1],
            'username': row[2],
            'email': row[3],
            'full_name': row[4],
            'branch': row[5],
            'is_active': row[6],
            'last_login': row[7],
            'role_name': row[8]
        })
    
    # Get roles for dropdown
    cursor.execute("SELECT role_id, role_name FROM roles ORDER BY role_name")
    roles = [{'role_id': r[0], 'role_name': r[1]} for r in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template('user_management.html', users=users, roles=roles)

@app.route('/create_user', methods=['POST'])
@login_required
@role_required('Super Admin')
def create_user():
    """Create a new user"""
    payroll_number = request.form.get('payroll_number')
    username = request.form.get('username')
    email = request.form.get('email')
    full_name = request.form.get('full_name')
    password = request.form.get('password')
    role_id = request.form.get('role_id')
    branch = request.form.get('branch')
    
    if not all([payroll_number, username, password, role_id]):
        flash('Please fill in all required fields', 'danger')
        return redirect(url_for('user_management'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        
        password_hash = hash_password(password)
        
        cursor.execute("""
            INSERT INTO aawsa_user (payroll_number, username, email, full_name, password_hash, role_id, branch, is_active)
            VALUES (%(payroll_number)s, %(username)s, %(email)s, %(full_name)s, %(password_hash)s, %(role_id)s, %(branch)s, TRUE)
        """, {
            'payroll_number': payroll_number,
            'username': username,
            'email': email,
            'full_name': full_name,
            'password_hash': password_hash,
            'role_id': role_id,
            'branch': branch
        })
        
        conn.commit()
        flash(f'User {username} created successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error creating user: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('user_management'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin')
def edit_user(user_id):
    """Edit existing user"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        role_id = request.form.get('role_id')
        branch = request.form.get('branch')
        is_active = request.form.get('is_active') == 'on'
        password = request.form.get('password')
        
        try:
            if password:
                password_hash = hash_password(password)
                cursor.execute("""
                    UPDATE aawsa_user 
                    SET username=%(username)s, email=%(email)s, full_name=%(full_name)s, 
                        role_id=%(role_id)s, branch=%(branch)s, is_active=%(is_active)s, password_hash=%(password_hash)s
                    WHERE user_id=%(user_id)s
                """, {
                    'username': username, 'email': email, 'full_name': full_name,
                    'role_id': role_id, 'branch': branch, 'is_active': is_active,
                    'password_hash': password_hash, 'user_id': user_id
                })
            else:
                cursor.execute("""
                    UPDATE aawsa_user 
                    SET username=%(username)s, email=%(email)s, full_name=%(full_name)s, 
                        role_id=%(role_id)s, branch=%(branch)s, is_active=%(is_active)s
                    WHERE user_id=%(user_id)s
                """, {
                    'username': username, 'email': email, 'full_name': full_name,
                    'role_id': role_id, 'branch': branch, 'is_active': is_active, 'user_id': user_id
                })
            
            conn.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('user_management'))
        except Exception as e:
            conn.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
    
    # GET request - load user data
    cursor.execute("""
        SELECT u.*, r.role_name
        FROM aawsa_user u
        LEFT JOIN roles r ON u.role_id = r.role_id
        WHERE u.user_id = %(user_id)s
    """, {'user_id': user_id})
    
    user_row = cursor.fetchone()
    if user_row:
        user = {
            'user_id': user_row[0],
            'payroll_number': user_row[1],
            'username': user_row[2],
            'email': user_row[3],
            'password_hash': user_row[4],
            'full_name': user_row[5],
            'branch': user_row[6],
            'last_login': user_row[7],
            'role_id': user_row[8],
            'is_active': user_row[11],
            'role_name': user_row[-1]
        }
    else:
        flash('User not found', 'danger')
        return redirect(url_for('user_management'))
    
    # Get roles for dropdown
    cursor.execute("SELECT role_id, role_name FROM roles ORDER BY role_name")
    roles = [{'role_id': r[0], 'role_name': r[1]} for r in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template('edit_user.html', user=user, roles=roles)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('Super Admin')
def delete_user(user_id):
    """Delete a user"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("DELETE FROM aawsa_user WHERE user_id = %(user_id)s", {'user_id': user_id})
        conn.commit()
        flash('User deleted successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('user_management'))

# ========================================
# ROLE MANAGEMENT ROUTES
# ========================================

@app.route('/manage_roles')
@login_required
@role_required('Super Admin')
def manage_roles():
    """Manage roles"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    cursor.execute("SELECT role_id, role_name, description FROM roles ORDER BY role_name")
    roles = []
    for row in cursor.fetchall():
        roles.append({
            'role_id': row[0],
            'role_name': row[1],
            'description': row[2]
        })
    
    cursor.close()
    conn.close()
    
    return render_template('manage_roles.html', roles=roles)

@app.route('/add_role', methods=['POST'])
@login_required
@role_required('Super Admin')
def add_role():
    """Add a new role"""
    role_name = request.form.get('role_name')
    description = request.form.get('description')
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute(
            "INSERT INTO roles (role_name, description) VALUES (%(role_name)s, %(description)s)",
            {'role_name': role_name, 'description': description}
        )
        conn.commit()
        flash(f'Role "{role_name}" created successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error creating role: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('manage_roles'))

@app.route('/delete_role/<int:role_id>', methods=['POST'])
@login_required
@role_required('Super Admin')
def delete_role(role_id):
    """Delete a role"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("DELETE FROM roles WHERE role_id = %(role_id)s", {'role_id': role_id})
        conn.commit()
        flash('Role deleted successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting role: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('manage_roles'))

@app.route('/roles/<int:role_id>/routes', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin')
def manage_role_routes(role_id):
    """Manage routes for a specific role"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    if request.method == 'POST':
        # Get selected routes from form
        selected_routes = request.form.getlist('routes')
        
        try:
            # Delete existing role-route mappings
            cursor.execute("DELETE FROM role_routes WHERE role_id = %(role_id)s", {'role_id': role_id})
            
            # Insert new mappings
            for route_id in selected_routes:
                cursor.execute(
                    "INSERT INTO role_routes (role_id, route_id) VALUES (%(role_id)s, %(route_id)s)",
                    {'role_id': role_id, 'route_id': route_id}
                )
            
            conn.commit()
            flash('Role permissions updated successfully', 'success')
            return redirect(url_for('manage_roles'))
        except Exception as e:
            conn.rollback()
            flash(f'Error updating permissions: {str(e)}', 'danger')
    
    # Get role info
    cursor.execute("SELECT role_name FROM roles WHERE role_id = %(role_id)s", {'role_id': role_id})
    role = cursor.fetchone()
    if not role:
        flash('Role not found', 'danger')
        return redirect(url_for('manage_roles'))
    
    role_name = role[0]
    
    # Get all routes
    cursor.execute("SELECT route_id, route_name, description FROM routes ORDER BY route_name")
    all_routes = [{'route_id': r[0], 'route_name': r[1], 'description': r[2]} for r in cursor.fetchall()]
    
    # Get current role routes
    cursor.execute("""
        SELECT route_id FROM role_routes WHERE role_id = %(role_id)s
    """, {'role_id': role_id})
    assigned_route_ids = [r[0] for r in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template('manage_role_routes.html', 
                         role_id=role_id, 
                         role_name=role_name, 
                         all_routes=all_routes, 
                         assigned_route_ids=assigned_route_ids)

@app.route('/routes', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin')
def manage_routes():
    """Manage application routes"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    if request.method == 'POST':
        route_name = request.form.get('route_name')
        endpoint = request.form.get('endpoint')
        description = request.form.get('description')
        
        try:
            cursor.execute("""
                INSERT INTO routes (route_name, endpoint, description)
                VALUES (%(route_name)s, %(endpoint)s, %(description)s)
            """, {'route_name': route_name, 'endpoint': endpoint, 'description': description})
            conn.commit()
            flash('Route created successfully', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error creating route: {str(e)}', 'danger')
    
    # Get all routes
    cursor.execute("SELECT route_id, route_name, endpoint, description FROM routes ORDER BY route_name")
    routes = []
    for row in cursor.fetchall():
        routes.append({
            'route_id': row[0],
            'route_name': row[1],
            'endpoint': row[2],
            'description': row[3]
        })
    
    cursor.close()
    conn.close()
    
    return render_template('manage_routes.html', routes=routes)

# ========================================
# APPLICATION INITIALIZATION
# ========================================

def initialize_app():
    """Initialize database tables and default data"""
    print("\n" + "="*60)
    print("Starting Application - Database Check")
    print("="*60)
    
    # Test database connection
    success, message = test_db_connection()
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")
        print("⚠ WARNING: Database is not available!")
        print("⚠ Application will start but you need to:")
        print("   1. Start your MySQL database (localhost:3306)")
        print("   2. Restart the application after database is up")
        print("="*60)
        return
    
    # Initialize RBAC tables
    if initialize_rbac_tables():
        print("✓ Database initialization completed")
    else:
        print("⚠ Database initialization failed but app will continue")
    
    print("="*60)
    
    # Initialize default roles and routes
    print("\nInitializing default roles and routes...")
    if initialize_default_roles_and_routes():
        print("✓ Default roles and routes setup completed")
    else:
        print("⚠ Default roles and routes setup failed but app will continue")
    print()

# ========================================
# MAIN APPLICATION ENTRY POINT
# ========================================

# ========================================
# LIBRARY MANAGEMENT ROUTES
# ========================================

@app.route('/manage_books', methods=['GET', 'POST'])
@login_required
def manage_books():
    """Manage library books - CRUD operations"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    book_data = {}
    
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        
        if action == 'delete':
            book_id = request.form.get('id')
            try:
                cursor.execute("DELETE FROM library_books WHERE id = %s", (book_id,))
                conn.commit()
                flash('Book deleted successfully!', 'success')
            except Exception as e:
                flash(f'Error deleting book: {str(e)}', 'danger')
        
        else:
            form_data = {
                'title': request.form.get('title'),
                'author': request.form.get('author'),
                'category': request.form.get('category'),
                'isbn': request.form.get('isbn'),
                'publisher': request.form.get('publisher'),
                'publication_year': request.form.get('publication_year') or None,
                'language': request.form.get('language'),
                'total_copies': request.form.get('total_copies', 1),
                'available_copies': request.form.get('available_copies', 1),
                'shelf_location': request.form.get('shelf_location'),
                'description': request.form.get('description'),
                'status': request.form.get('status', 'Active')
            }
            
            book_id = request.form.get('id')
            
            try:
                if book_id and action == 'edit':  # UPDATE
                    query = """
                        UPDATE library_books SET
                            title = %s, author = %s, category = %s, isbn = %s,
                            publisher = %s, publication_year = %s, language = %s,
                            total_copies = %s, available_copies = %s,
                            shelf_location = %s, description = %s, status = %s
                        WHERE id = %s
                    """
                    values = (
                        form_data['title'], form_data['author'], form_data['category'],
                        form_data['isbn'], form_data['publisher'], form_data['publication_year'],
                        form_data['language'], form_data['total_copies'], form_data['available_copies'],
                        form_data['shelf_location'], form_data['description'], form_data['status'],
                        book_id
                    )
                    cursor.execute(query, values)
                    flash('Book updated successfully!', 'success')
                
                else:  # INSERT
                    query = """
                        INSERT INTO library_books (
                            title, author, category, isbn, publisher, publication_year,
                            language, total_copies, available_copies, shelf_location,
                            description, status, created_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    values = (
                        form_data['title'], form_data['author'], form_data['category'],
                        form_data['isbn'], form_data['publisher'], form_data['publication_year'],
                        form_data['language'], form_data['total_copies'], form_data['available_copies'],
                        form_data['shelf_location'], form_data['description'], form_data['status'],
                        session.get('payroll_number', 'SYSTEM')
                    )
                    cursor.execute(query, values)
                    flash('Book added successfully!', 'success')
                
                conn.commit()
                
            except mysql.connector.IntegrityError as e:
                if 'Duplicate entry' in str(e) and 'isbn' in str(e):
                    flash('Error: A book with this ISBN already exists!', 'danger')
                else:
                    flash(f'Database error: {str(e)}', 'danger')
            except Exception as e:
                flash(f'Error saving book: {str(e)}', 'danger')
    
    # Handle edit request
    edit_id = request.args.get('edit_id')
    if edit_id:
        cursor.execute("SELECT * FROM library_books WHERE id = %s", (edit_id,))
        book_row = cursor.fetchone()
        if book_row:
            book_data = {
                'id': book_row[0],
                'title': book_row[1],
                'author': book_row[2],
                'category': book_row[3],
                'isbn': book_row[4],
                'publisher': book_row[5],
                'publication_year': book_row[6],
                'language': book_row[7],
                'total_copies': book_row[8],
                'available_copies': book_row[9],
                'borrowed_copies': book_row[10],
                'shelf_location': book_row[11],
                'description': book_row[12],
                'cover_image': book_row[13],
                'status': book_row[14]
            }
    
    # Get all books with pagination and search
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    status_filter = request.args.get('status', '').strip()
    
    query = "SELECT * FROM library_books WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND (title LIKE %s OR author LIKE %s OR isbn LIKE %s)"
        search_param = f"%{search_query}%"
        params.extend([search_param, search_param, search_param])
    
    if category_filter:
        query += " AND category = %s"
        params.append(category_filter)
    
    if status_filter:
        query += " AND status = %s"
        params.append(status_filter)
    
    query += " ORDER BY id DESC LIMIT 50"
    
    cursor.execute(query, params)
    books = cursor.fetchall()
    
    # Get statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_books,
            SUM(total_copies) as total_copies,
            SUM(available_copies) as available_copies,
            SUM(borrowed_copies) as borrowed_copies,
            COUNT(DISTINCT category) as total_categories
        FROM library_books
        WHERE status = 'Active'
    """)
    stats = cursor.fetchone()
    library_stats = {
        'total_books': stats[0] or 0,
        'total_copies': stats[1] or 0,
        'available_copies': stats[2] or 0,
        'borrowed_copies': stats[3] or 0,
        'total_categories': stats[4] or 0
    }
    
    # Get categories for filter dropdown
    cursor.execute("SELECT DISTINCT category FROM library_books WHERE category IS NOT NULL ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template('library_books.html',
                         books=books,
                         book_data=book_data,
                         library_stats=library_stats,
                         categories=categories,
                         search_query=search_query,
                         category_filter=category_filter,
                         status_filter=status_filter)

# ========================================
# BORROW MANAGEMENT ROUTES
# ========================================

@app.route('/borrow_management', methods=['GET', 'POST'])
@login_required
def borrow_management():
    """Manage book borrowing and returns"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'borrow':
            member_id = request.form.get('member_id')
            book_id = request.form.get('book_id')
            borrow_date = request.form.get('borrow_date') or date.today()
            due_date = request.form.get('due_date')
            notes = request.form.get('notes', '')
            
            try:
                # Check if book is available
                cursor.execute("SELECT available_copies FROM library_books WHERE id = %s", (book_id,))
                result = cursor.fetchone()
                
                if result and result[0] > 0:
                    # Insert borrowing record
                    cursor.execute("""
                        INSERT INTO book_borrowing (
                            member_id, book_id, borrow_date, due_date, status, notes, borrowed_by
                        ) VALUES (%s, %s, %s, %s, 'Borrowed', %s, %s)
                    """, (member_id, book_id, borrow_date, due_date, notes, session.get('payroll_number')))
                    
                    # Update book availability
                    cursor.execute("""
                        UPDATE library_books 
                        SET available_copies = available_copies - 1,
                            borrowed_copies = borrowed_copies + 1
                        WHERE id = %s
                    """, (book_id,))
                    
                    conn.commit()
                    flash('Book borrowed successfully!', 'success')
                else:
                    flash('This book is not available for borrowing.', 'warning')
                    
            except Exception as e:
                flash(f'Error processing borrow: {str(e)}', 'danger')
                conn.rollback()
        
        elif action == 'return':
            borrow_id = request.form.get('borrow_id')
            return_date = request.form.get('return_date') or date.today()
            
            try:
                # Get borrow record
                cursor.execute("SELECT book_id FROM book_borrowing WHERE id = %s", (borrow_id,))
                result = cursor.fetchone()
                
                if result:
                    book_id = result[0]
                    
                    # Update borrowing record
                    cursor.execute("""
                        UPDATE book_borrowing 
                        SET return_date = %s, status = 'Returned', returned_to = %s
                        WHERE id = %s
                    """, (return_date, session.get('payroll_number'), borrow_id))
                    
                    # Update book availability
                    cursor.execute("""
                        UPDATE library_books 
                        SET available_copies = available_copies + 1,
                            borrowed_copies = borrowed_copies - 1
                        WHERE id = %s
                    """, (book_id,))
                    
                    conn.commit()
                    flash('Book returned successfully!', 'success')
                else:
                    flash('Borrow record not found.', 'danger')
                    
            except Exception as e:
                flash(f'Error processing return: {str(e)}', 'danger')
                conn.rollback()
    
    # Get all members for dropdown
    cursor.execute("SELECT id, full_name FROM member_registration ORDER BY full_name")
    members = cursor.fetchall()
    
    # Get available books for dropdown
    cursor.execute("""
        SELECT id, title, author, available_copies 
        FROM library_books 
        WHERE status = 'Active' AND available_copies > 0
        ORDER BY title
    """)
    available_books = cursor.fetchall()
    
    # Get all borrowing records with member and book details
    cursor.execute("""
        SELECT 
            bb.id,
            m.full_name,
            lb.title,
            lb.author,
            bb.borrow_date,
            bb.due_date,
            bb.return_date,
            bb.status,
            bb.notes,
            DATEDIFF(CURDATE(), bb.due_date) as days_overdue
        FROM book_borrowing bb
        JOIN member_registration m ON bb.member_id = m.id
        JOIN library_books lb ON bb.book_id = lb.id
        ORDER BY bb.id DESC
        LIMIT 100
    """)
    borrowings = cursor.fetchall()
    
    # Update overdue status
    cursor.execute("""
        UPDATE book_borrowing 
        SET status = 'Overdue'
        WHERE status = 'Borrowed' AND due_date < CURDATE()
    """)
    conn.commit()
    
    # Get statistics
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN status = 'Borrowed' THEN 1 END) as currently_borrowed,
            COUNT(CASE WHEN status = 'Overdue' THEN 1 END) as overdue,
            COUNT(CASE WHEN status = 'Returned' THEN 1 END) as returned,
            COUNT(*) as total_transactions
        FROM book_borrowing
    """)
    stats = cursor.fetchone()
    borrow_stats = {
        'currently_borrowed': stats[0] or 0,
        'overdue': stats[1] or 0,
        'returned': stats[2] or 0,
        'total_transactions': stats[3] or 0
    }
    
    cursor.close()
    conn.close()
    
    return render_template('borrow_management.html',
                         members=members,
                         available_books=available_books,
                         borrowings=borrowings,
                         borrow_stats=borrow_stats)

# ========================================
# LIBRARY REPORTS
# ========================================

@app.route('/book_report')
@login_required
def book_report():
    """Library book report with filters and export"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    # Get filters
    category_filter = request.args.get('category', '')
    status_filter = request.args.get('status', '')
    language_filter = request.args.get('language', '')
    
    # Build query
    query = "SELECT * FROM library_books WHERE 1=1"
    params = []
    
    if category_filter:
        query += " AND category = %s"
        params.append(category_filter)
    
    if status_filter:
        query += " AND status = %s"
        params.append(status_filter)
    
    if language_filter:
        query += " AND language = %s"
        params.append(language_filter)
    
    query += " ORDER BY category, title"
    
    cursor.execute(query, params)
    books = cursor.fetchall()
    
    # Get summary statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_books,
            SUM(total_copies) as total_copies,
            SUM(available_copies) as available_copies,
            SUM(borrowed_copies) as borrowed_copies,
            COUNT(DISTINCT category) as categories,
            COUNT(CASE WHEN available_copies = 0 THEN 1 END) as out_of_stock
        FROM library_books
        WHERE status = 'Active'
    """)
    stats = cursor.fetchone()
    summary_stats = {
        'total_books': stats[0] or 0,
        'total_copies': stats[1] or 0,
        'available': stats[2] or 0,
        'borrowed': stats[3] or 0,
        'categories': stats[4] or 0,
        'out_of_stock': stats[5] or 0
    }
    
    # Get filter options
    cursor.execute("SELECT DISTINCT category FROM library_books WHERE category IS NOT NULL ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT DISTINCT language FROM library_books WHERE language IS NOT NULL ORDER BY language")
    languages = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template('book_report.html',
                         books=books,
                         summary_stats=summary_stats,
                         categories=categories,
                         languages=languages,
                         category_filter=category_filter,
                         status_filter=status_filter,
                         language_filter=language_filter)

@app.route('/borrow_report')
@login_required
def borrow_report():
    """Borrow transactions report with filters and export"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    # Get filters
    member_filter = request.args.get('member_id', '')
    book_filter = request.args.get('book_id', '')
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Build query
    query = """
        SELECT 
            bb.id,
            m.full_name as member_name,
            lb.title as book_title,
            lb.author,
            bb.borrow_date,
            bb.due_date,
            bb.return_date,
            bb.status,
            DATEDIFF(CURDATE(), bb.due_date) as days_overdue,
            bb.notes
        FROM book_borrowing bb
        JOIN member_registration m ON bb.member_id = m.id
        JOIN library_books lb ON bb.book_id = lb.id
        WHERE 1=1
    """
    params = []
    
    if member_filter:
        query += " AND bb.member_id = %s"
        params.append(member_filter)
    
    if book_filter:
        query += " AND bb.book_id = %s"
        params.append(book_filter)
    
    if status_filter:
        query += " AND bb.status = %s"
        params.append(status_filter)
    
    if date_from:
        query += " AND bb.borrow_date >= %s"
        params.append(date_from)
    
    if date_to:
        query += " AND bb.borrow_date <= %s"
        params.append(date_to)
    
    query += " ORDER BY bb.borrow_date DESC"
    
    cursor.execute(query, params)
    transactions = cursor.fetchall()
    
    # Get statistics
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN status = 'Borrowed' THEN 1 END) as borrowed,
            COUNT(CASE WHEN status = 'Overdue' THEN 1 END) as overdue,
            COUNT(CASE WHEN status = 'Returned' THEN 1 END) as returned,
            COUNT(*) as total
        FROM book_borrowing
    """)
    stats = cursor.fetchone()
    summary_stats = {
        'borrowed': stats[0] or 0,
        'overdue': stats[1] or 0,
        'returned': stats[2] or 0,
        'total': stats[3] or 0
    }
    
    # Get members and books for filter dropdowns
    cursor.execute("SELECT id, full_name FROM member_registration ORDER BY full_name")
    members = cursor.fetchall()
    
    cursor.execute("SELECT id, title FROM library_books ORDER BY title")
    books_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('borrow_report.html',
                         transactions=transactions,
                         summary_stats=summary_stats,
                         members=members,
                         books_list=books_list,
                         member_filter=member_filter,
                         book_filter=book_filter,
                         status_filter=status_filter,
                         date_from=date_from,
                         date_to=date_to)

# ========================================
# MEWACO (CONTRIBUTION) MANAGEMENT ROUTES
# ========================================

@app.route('/mewaco_types', methods=['GET', 'POST'])
@login_required
def mewaco_types():
    """Manage MEWACO contribution types"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    type_data = {}
    
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        
        if action == 'delete':
            type_id = request.form.get('id')
            try:
                cursor.execute("DELETE FROM mewaco_types WHERE id = %s", (type_id,))
                conn.commit()
                flash('Contribution type deleted successfully!', 'success')
            except Exception as e:
                flash(f'Error deleting type: {str(e)}', 'danger')
        
        else:
            form_data = {
                'type_name': request.form.get('type_name'),
                'description': request.form.get('description'),
                'default_amount': request.form.get('default_amount', 0),
                'status': request.form.get('status', 'Active')
            }
            
            type_id = request.form.get('id')
            
            try:
                if type_id and action == 'edit':  # UPDATE
                    query = """
                        UPDATE mewaco_types SET
                            type_name = %s, description = %s, 
                            default_amount = %s, status = %s
                        WHERE id = %s
                    """
                    values = (
                        form_data['type_name'], form_data['description'],
                        form_data['default_amount'], form_data['status'], type_id
                    )
                    cursor.execute(query, values)
                    flash('Contribution type updated successfully!', 'success')
                
                else:  # INSERT
                    query = """
                        INSERT INTO mewaco_types (
                            type_name, description, default_amount, status, created_by
                        ) VALUES (%s, %s, %s, %s, %s)
                    """
                    values = (
                        form_data['type_name'], form_data['description'],
                        form_data['default_amount'], form_data['status'],
                        session.get('payroll_number', 'SYSTEM')
                    )
                    cursor.execute(query, values)
                    flash('Contribution type added successfully!', 'success')
                
                conn.commit()
                
            except mysql.connector.IntegrityError as e:
                if 'Duplicate entry' in str(e):
                    flash('Error: A contribution type with this name already exists!', 'danger')
                else:
                    flash(f'Database error: {str(e)}', 'danger')
            except Exception as e:
                flash(f'Error saving type: {str(e)}', 'danger')
    
    # Handle edit request
    edit_id = request.args.get('edit_id')
    if edit_id:
        cursor.execute("SELECT * FROM mewaco_types WHERE id = %s", (edit_id,))
        type_row = cursor.fetchone()
        if type_row:
            type_data = {
                'id': type_row[0],
                'type_name': type_row[1],
                'description': type_row[2],
                'default_amount': type_row[3],
                'status': type_row[4]
            }
    
    # Get all contribution types
    cursor.execute("SELECT * FROM mewaco_types ORDER BY id DESC")
    types = cursor.fetchall()
    
    # Get statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_types,
            COUNT(CASE WHEN status = 'Active' THEN 1 END) as active_types,
            SUM(default_amount) as total_default_amount
        FROM mewaco_types
    """)
    stats = cursor.fetchone()
    type_stats = {
        'total_types': stats[0] or 0,
        'active_types': stats[1] or 0,
        'total_default': stats[2] or 0
    }
    
    cursor.close()
    conn.close()
    
    return render_template('mewaco_types.html',
                         types=types,
                         type_data=type_data,
                         type_stats=type_stats)

@app.route('/mewaco_contributions', methods=['GET', 'POST'])
@login_required
def mewaco_contributions():
    """Manage monthly/user-based contributions"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        
        if action == 'delete':
            contrib_id = request.form.get('id')
            try:
                cursor.execute("DELETE FROM mewaco_contributions WHERE id = %s", (contrib_id,))
                conn.commit()
                flash('Contribution deleted successfully!', 'success')
            except Exception as e:
                flash(f'Error deleting contribution: {str(e)}', 'danger')
        
        else:
            form_data = {
                'member_id': request.form.get('member_id'),
                'mewaco_type_id': request.form.get('mewaco_type_id'),
                'contribution_date': request.form.get('contribution_date') or date.today(),
                'amount': request.form.get('amount', 0),
                'payment_method': request.form.get('payment_method', 'Cash'),
                'receipt_number': request.form.get('receipt_number'),
                'notes': request.form.get('notes', '')
            }
            
            contrib_id = request.form.get('id')
            
            try:
                if contrib_id and action == 'edit':  # UPDATE
                    query = """
                        UPDATE mewaco_contributions SET
                            member_id = %s, mewaco_type_id = %s, contribution_date = %s,
                            amount = %s, payment_method = %s, receipt_number = %s, notes = %s
                        WHERE id = %s
                    """
                    values = (
                        form_data['member_id'], form_data['mewaco_type_id'], 
                        form_data['contribution_date'], form_data['amount'],
                        form_data['payment_method'], form_data['receipt_number'],
                        form_data['notes'], contrib_id
                    )
                    cursor.execute(query, values)
                    flash('Contribution updated successfully!', 'success')
                
                else:  # INSERT
                    query = """
                        INSERT INTO mewaco_contributions (
                            member_id, mewaco_type_id, contribution_date, amount,
                            payment_method, receipt_number, notes, recorded_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    values = (
                        form_data['member_id'], form_data['mewaco_type_id'],
                        form_data['contribution_date'], form_data['amount'],
                        form_data['payment_method'], form_data['receipt_number'],
                        form_data['notes'], session.get('payroll_number', 'SYSTEM')
                    )
                    cursor.execute(query, values)
                    flash('Contribution recorded successfully!', 'success')
                
                conn.commit()
                
            except Exception as e:
                flash(f'Error saving contribution: {str(e)}', 'danger')
                conn.rollback()
    
    # Get filters
    member_filter = request.args.get('member_id', '')
    type_filter = request.args.get('type_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Build query for contributions
    query = """
        SELECT 
            mc.id, m.full_name, mt.type_name, mc.contribution_date,
            mc.amount, mc.payment_method, mc.receipt_number, mc.notes
        FROM mewaco_contributions mc
        JOIN member_registration m ON mc.member_id = m.id
        JOIN mewaco_types mt ON mc.mewaco_type_id = mt.id
        WHERE 1=1
    """
    params = []
    
    if member_filter:
        query += " AND mc.member_id = %s"
        params.append(member_filter)
    
    if type_filter:
        query += " AND mc.mewaco_type_id = %s"
        params.append(type_filter)
    
    if date_from:
        query += " AND mc.contribution_date >= %s"
        params.append(date_from)
    
    if date_to:
        query += " AND mc.contribution_date <= %s"
        params.append(date_to)
    
    query += " ORDER BY mc.contribution_date DESC LIMIT 100"
    
    cursor.execute(query, params)
    contributions = cursor.fetchall()
    
    # Get members and types for dropdowns
    cursor.execute("SELECT id, full_name FROM member_registration ORDER BY full_name")
    members = cursor.fetchall()
    
    cursor.execute("SELECT id, type_name, default_amount FROM mewaco_types WHERE status = 'Active' ORDER BY type_name")
    mewaco_types = cursor.fetchall()
    
    # Get statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_contributions,
            SUM(amount) as total_amount,
            COUNT(DISTINCT member_id) as unique_contributors,
            COUNT(DISTINCT mewaco_type_id) as types_used
        FROM mewaco_contributions
    """)
    stats = cursor.fetchone()
    contrib_stats = {
        'total_contributions': stats[0] or 0,
        'total_amount': stats[1] or 0,
        'unique_contributors': stats[2] or 0,
        'types_used': stats[3] or 0
    }
    
    cursor.close()
    conn.close()
    
    return render_template('mewaco_contributions.html',
                         members=members,
                         mewaco_types=mewaco_types,
                         contributions=contributions,
                         contrib_stats=contrib_stats,
                         member_filter=member_filter,
                         type_filter=type_filter,
                         date_from=date_from,
                         date_to=date_to)

@app.route('/monthly_contributions', methods=['GET', 'POST'])
@login_required
def monthly_contributions():
    """Bulk monthly contribution collection page"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    # Get selected month/year and type
    selected_month = request.args.get('month') or datetime.now().strftime('%Y-%m')
    selected_type_id = request.args.get('type_id', '')
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'bulk_save':
            # Process bulk contribution data
            contribution_type_id = request.form.get('contribution_type_id')
            contribution_month = request.form.get('contribution_month')
            
            try:
                saved_count = 0
                for key in request.form:
                    if key.startswith('amount_'):
                        member_id = key.split('_')[1]
                        amount = request.form.get(key)
                        status = request.form.get(f'status_{member_id}', 'Unpaid')
                        
                        if amount and float(amount) > 0 and status == 'Paid':
                            # Record contribution
                            cursor.execute("""
                                INSERT INTO mewaco_contributions (
                                    member_id, mewaco_type_id, contribution_date, amount,
                                    payment_method, notes, recorded_by
                                ) VALUES (%s, %s, %s, %s, 'Cash', %s, %s)
                            """, (
                                member_id, contribution_type_id, contribution_month + '-01',
                                amount, f'Monthly contribution - {contribution_month}',
                                session.get('payroll_number', 'SYSTEM')
                            ))
                            saved_count += 1
                
                conn.commit()
                flash(f'Successfully recorded {saved_count} contributions!', 'success')
                
            except Exception as e:
                flash(f'Error saving contributions: {str(e)}', 'danger')
                conn.rollback()
        
        elif action == 'bulk_upload':
            # Handle Excel/CSV upload
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename:
                    try:
                        df = pd.read_excel(file) if file.filename.endswith('.xlsx') else pd.read_csv(file)
                        
                        saved_count = 0
                        for _, row in df.iterrows():
                            cursor.execute("""
                                SELECT id FROM member_registration WHERE full_name = %s
                            """, (row['Member Name'],))
                            member = cursor.fetchone()
                            
                            if member:
                                cursor.execute("""
                                    INSERT INTO mewaco_contributions (
                                        member_id, mewaco_type_id, contribution_date, amount,
                                        payment_method, recorded_by
                                    ) VALUES (%s, %s, %s, %s, %s, %s)
                                """, (
                                    member[0], request.form.get('upload_type_id'),
                                    row['Date'], row['Amount'], row.get('Payment Method', 'Cash'),
                                    session.get('payroll_number', 'SYSTEM')
                                ))
                                saved_count += 1
                        
                        conn.commit()
                        flash(f'Successfully uploaded {saved_count} contributions!', 'success')
                        
                    except Exception as e:
                        flash(f'Error processing upload: {str(e)}', 'danger')
                        conn.rollback()
    
    # Get all members
    cursor.execute("SELECT id, full_name, section_name FROM member_registration ORDER BY section_name, full_name")
    members = cursor.fetchall()
    
    # Get active contribution types
    cursor.execute("SELECT id, type_name, default_amount FROM mewaco_types WHERE status = 'Active' ORDER BY type_name")
    mewaco_types = cursor.fetchall()
    
    # Get existing contributions for selected month and type
    existing_contributions = {}
    if selected_type_id and selected_month:
        cursor.execute("""
            SELECT member_id, SUM(amount) as total_amount
            FROM mewaco_contributions
            WHERE mewaco_type_id = %s 
            AND DATE_FORMAT(contribution_date, '%%Y-%%m') = %s
            GROUP BY member_id
        """, (selected_type_id, selected_month))
        existing_contributions = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Calculate summary
    if selected_type_id and members:
        cursor.execute("SELECT default_amount FROM mewaco_types WHERE id = %s", (selected_type_id,))
        default_amt = cursor.fetchone()
        default_amount = default_amt[0] if default_amt else 0
        
        total_expected = len(members) * default_amount
        total_collected = sum(existing_contributions.values())
        total_outstanding = total_expected - total_collected
        paid_count = len(existing_contributions)
        unpaid_count = len(members) - paid_count
    else:
        total_expected = 0
        total_collected = 0
        total_outstanding = 0
        paid_count = 0
        unpaid_count = len(members) if members else 0
    
    summary = {
        'total_expected': total_expected,
        'total_collected': total_collected,
        'total_outstanding': total_outstanding,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count
    }
    
    cursor.close()
    conn.close()
    
    return render_template('monthly_contributions.html',
                         members=members,
                         mewaco_types=mewaco_types,
                         selected_month=selected_month,
                         selected_type_id=selected_type_id,
                         existing_contributions=existing_contributions,
                         summary=summary)

@app.route('/contribution_report_monthly')
@login_required
def contribution_report_monthly():
    """Monthly contribution report with trends"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    # Get filters
    type_filter = request.args.get('type_id', '')
    month_filter = request.args.get('month', '')
    year_filter = request.args.get('year', datetime.now().year)
    
    # Get contribution types for dropdown
    cursor.execute("SELECT id, type_name FROM mewaco_types ORDER BY type_name")
    contrib_types = cursor.fetchall()
    
    # Build query
    query = """
        SELECT 
            DATE_FORMAT(mc.contribution_date, '%%Y-%%m') as month,
            mt.type_name,
            COUNT(DISTINCT mc.member_id) as contributor_count,
            SUM(mc.amount) as total_amount,
            COUNT(*) as transaction_count
        FROM mewaco_contributions mc
        JOIN mewaco_types mt ON mc.mewaco_type_id = mt.id
        WHERE YEAR(mc.contribution_date) = %s
    """
    params = [year_filter]
    
    if type_filter:
        query += " AND mc.mewaco_type_id = %s"
        params.append(type_filter)
    
    if month_filter:
        query += " AND DATE_FORMAT(mc.contribution_date, '%%Y-%%m') = %s"
        params.append(month_filter)
    
    query += " GROUP BY month, mt.type_name ORDER BY month DESC, mt.type_name"
    
    cursor.execute(query, params)
    monthly_data = cursor.fetchall()
    
    # Get chart data for trends (last 12 months)
    cursor.execute("""
        SELECT 
            DATE_FORMAT(contribution_date, '%%Y-%%m') as month,
            SUM(amount) as total
        FROM mewaco_contributions
        WHERE contribution_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY month
        ORDER BY month
    """)
    chart_data = cursor.fetchall()
    chart_labels = [row[0] for row in chart_data]
    chart_amounts = [float(row[1]) for row in chart_data]
    
    # Overall statistics
    cursor.execute("""
        SELECT 
            SUM(amount) as grand_total,
            COUNT(*) as total_transactions,
            COUNT(DISTINCT member_id) as unique_contributors
        FROM mewaco_contributions
        WHERE YEAR(contribution_date) = %s
    """, (year_filter,))
    stats = cursor.fetchone()
    overall_stats = {
        'grand_total': stats[0] or 0,
        'total_transactions': stats[1] or 0,
        'unique_contributors': stats[2] or 0
    }
    
    cursor.close()
    conn.close()
    
    return render_template('contribution_report_monthly.html',
                         monthly_data=monthly_data,
                         contrib_types=contrib_types,
                         chart_labels=chart_labels,
                         chart_amounts=chart_amounts,
                         overall_stats=overall_stats,
                         type_filter=type_filter,
                         month_filter=month_filter,
                         year_filter=year_filter)

@app.route('/member_contribution_summary')
@login_required
def member_contribution_summary():
    """Individual member contribution summary and history"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    # Get filters
    member_filter = request.args.get('member_id', '')
    year_filter = request.args.get('year', datetime.now().year)
    
    # Get all members for dropdown
    cursor.execute("SELECT id, full_name FROM member_registration ORDER BY full_name")
    members = cursor.fetchall()
    
    # Get member contribution summary
    query = """
        SELECT 
            m.full_name,
            mt.type_name,
            COUNT(*) as payment_count,
            SUM(mc.amount) as total_paid,
            MIN(mc.contribution_date) as first_payment,
            MAX(mc.contribution_date) as last_payment
        FROM mewaco_contributions mc
        JOIN member_registration m ON mc.member_id = m.id
        JOIN mewaco_types mt ON mc.mewaco_type_id = mt.id
        WHERE YEAR(mc.contribution_date) = %s
    """
    params = [year_filter]
    
    if member_filter:
        query += " AND mc.member_id = %s"
        params.append(member_filter)
    
    query += " GROUP BY m.full_name, mt.type_name ORDER BY m.full_name, mt.type_name"
    
    cursor.execute(query, params)
    member_summary = cursor.fetchall()
    
    # Get detailed transaction history if member is selected
    transaction_history = []
    if member_filter:
        cursor.execute("""
            SELECT 
                mc.contribution_date,
                mt.type_name,
                mc.amount,
                mc.payment_method,
                mc.receipt_number,
                mc.notes
            FROM mewaco_contributions mc
            JOIN mewaco_types mt ON mc.mewaco_type_id = mt.id
            WHERE mc.member_id = %s
            AND YEAR(mc.contribution_date) = %s
            ORDER BY mc.contribution_date DESC
        """, (member_filter, year_filter))
        transaction_history = cursor.fetchall()
    
    # Get overall statistics
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT m.id) as total_contributors,
            SUM(mc.amount) as grand_total,
            AVG(mc.amount) as average_contribution
        FROM mewaco_contributions mc
        JOIN member_registration m ON mc.member_id = m.id
        WHERE YEAR(mc.contribution_date) = %s
    """, (year_filter,))
    stats = cursor.fetchone()
    summary_stats = {
        'total_contributors': stats[0] or 0,
        'grand_total': stats[1] or 0,
        'average_contribution': stats[2] or 0
    }
    
    cursor.close()
    conn.close()
    
    return render_template('member_contribution_summary.html',
                         members=members,
                         member_summary=member_summary,
                         transaction_history=transaction_history,
                         summary_stats=summary_stats,
                         member_filter=member_filter,
                         year_filter=year_filter)

# ========================================
# MEDEBE (SECTION & SUB-SECTION) MANAGEMENT ROUTES
# ========================================

@app.route('/medebe_management', methods=['GET', 'POST'])
@login_required
def medebe_management():
    """Manage medebe (sub-sections)"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    medebe_data = {}
    
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        
        if action == 'delete':
            medebe_id = request.form.get('id')
            try:
                cursor.execute("DELETE FROM medebe WHERE id = %s", (medebe_id,))
                conn.commit()
                flash('Medebe deleted successfully!', 'success')
            except Exception as e:
                flash(f'Error deleting medebe: {str(e)}', 'danger')
        
        else:
            form_data = {
                'medebe_name': request.form.get('medebe_name'),
                'section_name': request.form.get('section_name'),
                'description': request.form.get('description', ''),
                'created_date': request.form.get('created_date') or date.today()
            }
            
            medebe_id = request.form.get('id')
            
            try:
                if medebe_id and action == 'edit':  # UPDATE
                    query = """
                        UPDATE medebe SET
                            medebe_name = %s, section_name = %s, 
                            description = %s, created_date = %s
                        WHERE id = %s
                    """
                    values = (
                        form_data['medebe_name'], form_data['section_name'],
                        form_data['description'], form_data['created_date'], medebe_id
                    )
                    cursor.execute(query, values)
                    flash('Medebe updated successfully!', 'success')
                
                else:  # INSERT
                    query = """
                        INSERT INTO medebe (
                            medebe_name, section_name, description, created_date, created_by
                        ) VALUES (%s, %s, %s, %s, %s)
                    """
                    values = (
                        form_data['medebe_name'], form_data['section_name'],
                        form_data['description'], form_data['created_date'],
                        session.get('payroll_number', 'SYSTEM')
                    )
                    cursor.execute(query, values)
                    flash('Medebe added successfully!', 'success')
                
                conn.commit()
                
            except Exception as e:
                flash(f'Error saving medebe: {str(e)}', 'danger')
    
    # Handle edit request
    edit_id = request.args.get('edit_id')
    if edit_id:
        cursor.execute("SELECT * FROM medebe WHERE id = %s", (edit_id,))
        medebe_row = cursor.fetchone()
        if medebe_row:
            medebe_data = {
                'id': medebe_row[0],
                'medebe_name': medebe_row[1],
                'section_name': medebe_row[2],
                'description': medebe_row[3],
                'created_date': medebe_row[4]
            }
    
    # Get filters
    section_filter = request.args.get('section', '')
    search = request.args.get('search', '')
    
    # Build query
    query = "SELECT * FROM medebe WHERE 1=1"
    params = []
    
    if section_filter:
        query += " AND section_name = %s"
        params.append(section_filter)
    
    if search:
        query += " AND (medebe_name LIKE %s OR description LIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    query += " ORDER BY section_name, id DESC"
    
    cursor.execute(query, params)
    medebes = cursor.fetchall()
    
    # Get statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_medebes,
            COUNT(DISTINCT section_name) as sections_with_medebes
        FROM medebe
    """)
    stats = cursor.fetchone()
    medebe_stats = {
        'total_medebes': stats[0] or 0,
        'sections_with_medebes': stats[1] or 0
    }
    
    # Get member counts per medebe
    cursor.execute("""
        SELECT m.id, m.medebe_name, COUNT(mma.id) as member_count
        FROM medebe m
        LEFT JOIN member_medebe_assignment mma ON m.id = mma.medebe_id
        GROUP BY m.id, m.medebe_name
    """)
    member_counts = {row[0]: row[2] for row in cursor.fetchall()}
    
    cursor.close()
    conn.close()
    
    return render_template('medebe_management.html',
                         medebes=medebes,
                         medebe_data=medebe_data,
                         medebe_stats=medebe_stats,
                         member_counts=member_counts,
                         section_filter=section_filter,
                         search=search)

@app.route('/member_medebe_assignment', methods=['GET', 'POST'])
@login_required
def member_medebe_assignment():
    """Assign members to medebe (sub-sections)"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'assign':
            member_id = request.form.get('member_id')
            medebe_id = request.form.get('medebe_id')
            
            try:
                # Get member's section and medebe's section
                cursor.execute("SELECT section_name FROM member_registration WHERE id = %s", (member_id,))
                member_section = cursor.fetchone()[0]
                
                cursor.execute("SELECT section_name FROM medebe WHERE id = %s", (medebe_id,))
                medebe_section = cursor.fetchone()[0]
                
                # Validation: member and medebe must be in same section
                if member_section != medebe_section:
                    flash(f'Error: Member from {member_section} cannot be assigned to medebe in {medebe_section}!', 'danger')
                else:
                    # Check if already assigned
                    cursor.execute("SELECT id FROM member_medebe_assignment WHERE member_id = %s", (member_id,))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing assignment
                        cursor.execute("""
                            UPDATE member_medebe_assignment 
                            SET medebe_id = %s, section_name = %s, assigned_date = %s, 
                                assigned_by = %s, assignment_method = 'Manual'
                            WHERE member_id = %s
                        """, (medebe_id, member_section, date.today(), 
                              session.get('payroll_number', 'SYSTEM'), member_id))
                        flash('Member reassigned successfully!', 'success')
                    else:
                        # Insert new assignment
                        cursor.execute("""
                            INSERT INTO member_medebe_assignment (
                                member_id, medebe_id, section_name, assigned_date, 
                                assigned_by, assignment_method
                            ) VALUES (%s, %s, %s, %s, %s, 'Manual')
                        """, (member_id, medebe_id, member_section, date.today(),
                              session.get('payroll_number', 'SYSTEM')))
                        flash('Member assigned successfully!', 'success')
                    
                    conn.commit()
                    
            except Exception as e:
                flash(f'Error assigning member: {str(e)}', 'danger')
                conn.rollback()
        
        elif action == 'auto_assign':
            section_name = request.form.get('section_name')
            
            try:
                # Get all unassigned members in this section
                cursor.execute("""
                    SELECT m.id FROM member_registration m
                    LEFT JOIN member_medebe_assignment mma ON m.id = mma.member_id
                    WHERE m.section_name = %s AND mma.id IS NULL
                """, (section_name,))
                unassigned_members = [row[0] for row in cursor.fetchall()]
                
                # Get all medebes for this section
                cursor.execute("SELECT id FROM medebe WHERE section_name = %s ORDER BY id", (section_name,))
                medebes = [row[0] for row in cursor.fetchall()]
                
                if not medebes:
                    flash(f'No medebe found for {section_name}!', 'danger')
                elif not unassigned_members:
                    flash(f'All members in {section_name} are already assigned!', 'info')
                else:
                    # Distribute members evenly across medebes
                    import random
                    random.shuffle(unassigned_members)
                    
                    assigned_count = 0
                    for i, member_id in enumerate(unassigned_members):
                        medebe_id = medebes[i % len(medebes)]
                        cursor.execute("""
                            INSERT INTO member_medebe_assignment (
                                member_id, medebe_id, section_name, assigned_date,
                                assigned_by, assignment_method
                            ) VALUES (%s, %s, %s, %s, %s, 'Auto')
                        """, (member_id, medebe_id, section_name, date.today(),
                              session.get('payroll_number', 'SYSTEM')))
                        assigned_count += 1
                    
                    conn.commit()
                    flash(f'Successfully auto-assigned {assigned_count} members to {len(medebes)} medebe groups!', 'success')
                    
            except Exception as e:
                flash(f'Error in auto-assignment: {str(e)}', 'danger')
                conn.rollback()
        
        elif action == 'remove':
            member_id = request.form.get('member_id')
            try:
                cursor.execute("DELETE FROM member_medebe_assignment WHERE member_id = %s", (member_id,))
                conn.commit()
                flash('Member removed from medebe!', 'success')
            except Exception as e:
                flash(f'Error removing member: {str(e)}', 'danger')
    
    # Get filters
    section_filter = request.args.get('section', '')
    medebe_filter = request.args.get('medebe', '')
    status_filter = request.args.get('status', '')
    
    # Get all sections
    sections = ['የሕፃናት ክፍል', 'ማህከላዊያን ክፍል', 'ወጣት ክፍል', 'ወላጅ ክፍል']
    
    # Get medebes for filter
    if section_filter:
        cursor.execute("SELECT id, medebe_name FROM medebe WHERE section_name = %s ORDER BY medebe_name", (section_filter,))
    else:
        cursor.execute("SELECT id, medebe_name FROM medebe ORDER BY section_name, medebe_name")
    medebes = cursor.fetchall()
    
    # Build member query
    query = """
        SELECT 
            m.id, m.full_name, m.phone, m.section_name,
            mma.medebe_id, meb.medebe_name, mma.assigned_date
        FROM member_registration m
        LEFT JOIN member_medebe_assignment mma ON m.id = mma.member_id
        LEFT JOIN medebe meb ON mma.medebe_id = meb.id
        WHERE 1=1
    """
    params = []
    
    if section_filter:
        query += " AND m.section_name = %s"
        params.append(section_filter)
    
    if medebe_filter:
        query += " AND mma.medebe_id = %s"
        params.append(medebe_filter)
    
    if status_filter == 'Assigned':
        query += " AND mma.id IS NOT NULL"
    elif status_filter == 'Not Assigned':
        query += " AND mma.id IS NULL"
    
    query += " ORDER BY m.section_name, m.full_name"
    
    cursor.execute(query, params)
    members = cursor.fetchall()
    
    # Get statistics
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT m.id) as total_members,
            COUNT(DISTINCT mma.id) as assigned_members
        FROM member_registration m
        LEFT JOIN member_medebe_assignment mma ON m.id = mma.member_id
    """)
    stats = cursor.fetchone()
    assignment_stats = {
        'total_members': stats[0] or 0,
        'assigned_members': stats[1] or 0,
        'unassigned_members': (stats[0] or 0) - (stats[1] or 0)
    }
    
    # Get medebes for assignment dropdown
    cursor.execute("SELECT id, medebe_name, section_name FROM medebe ORDER BY section_name, medebe_name")
    all_medebes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('member_medebe_assignment.html',
                         members=members,
                         medebes=medebes,
                         all_medebes=all_medebes,
                         sections=sections,
                         assignment_stats=assignment_stats,
                         section_filter=section_filter,
                         medebe_filter=medebe_filter,
                         status_filter=status_filter)

@app.route('/medebe_report')
@login_required
def medebe_report():
    """Medebe statistics and reports"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    # Get filter
    section_filter = request.args.get('section', '')
    
    # Build query for medebe summary
    query = """
        SELECT 
            m.id, m.medebe_name, m.section_name, m.created_date, m.description,
            COUNT(mma.id) as member_count
        FROM medebe m
        LEFT JOIN member_medebe_assignment mma ON m.id = mma.medebe_id
    """
    params = []
    
    if section_filter:
        query += " WHERE m.section_name = %s"
        params.append(section_filter)
    
    query += " GROUP BY m.id, m.medebe_name, m.section_name, m.created_date, m.description"
    query += " ORDER BY m.section_name, m.medebe_name"
    
    cursor.execute(query, params)
    medebe_summary = cursor.fetchall()
    
    # Get overall statistics
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT m.id) as total_medebes,
            COUNT(DISTINCT m.section_name) as total_sections,
            COUNT(DISTINCT mma.member_id) as total_assigned_members
        FROM medebe m
        LEFT JOIN member_medebe_assignment mma ON m.id = mma.medebe_id
    """)
    stats = cursor.fetchone()
    overall_stats = {
        'total_medebes': stats[0] or 0,
        'total_sections': stats[1] or 0,
        'total_assigned_members': stats[2] or 0
    }
    
    # Get chart data (members per medebe by section)
    cursor.execute("""
        SELECT m.section_name, m.medebe_name, COUNT(mma.id) as member_count
        FROM medebe m
        LEFT JOIN member_medebe_assignment mma ON m.id = mma.medebe_id
        GROUP BY m.section_name, m.medebe_name
        ORDER BY m.section_name, m.medebe_name
    """)
    chart_data = cursor.fetchall()
    
    # Organize chart data by section
    sections_chart = {}
    for row in chart_data:
        section = row[0]
        if section not in sections_chart:
            sections_chart[section] = {'labels': [], 'values': []}
        sections_chart[section]['labels'].append(row[1])
        sections_chart[section]['values'].append(row[2])
    
    sections = ['የሕፃናት ክፍል', 'ማህከላዊያን ክፍል', 'ወጣት ክፍል', 'ወላጅ ክፍል']
    
    cursor.close()
    conn.close()
    
    return render_template('medebe_report.html',
                         medebe_summary=medebe_summary,
                         overall_stats=overall_stats,
                         sections_chart=sections_chart,
                         sections=sections,
                         section_filter=section_filter)

@app.route('/member_medebe_report')
@login_required
def member_medebe_report():
    """Member to medebe assignment report"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    # Get filters
    section_filter = request.args.get('section', '')
    medebe_filter = request.args.get('medebe', '')
    
    # Build query
    query = """
        SELECT 
            m.full_name, m.phone, m.section_name,
            meb.medebe_name, mma.assigned_date, mma.assignment_method
        FROM member_registration m
        INNER JOIN member_medebe_assignment mma ON m.id = mma.member_id
        INNER JOIN medebe meb ON mma.medebe_id = meb.id
        WHERE 1=1
    """
    params = []
    
    if section_filter:
        query += " AND m.section_name = %s"
        params.append(section_filter)
    
    if medebe_filter:
        query += " AND mma.medebe_id = %s"
        params.append(medebe_filter)
    
    query += " ORDER BY m.section_name, meb.medebe_name, m.full_name"
    
    cursor.execute(query, params)
    member_assignments = cursor.fetchall()
    
    # Get medebes for filter
    cursor.execute("SELECT id, medebe_name, section_name FROM medebe ORDER BY section_name, medebe_name")
    medebes = cursor.fetchall()
    
    # Get statistics
    cursor.execute("""
        SELECT 
            m.section_name,
            COUNT(DISTINCT mma.member_id) as assigned_count,
            COUNT(DISTINCT meb.id) as medebe_count
        FROM member_registration m
        INNER JOIN member_medebe_assignment mma ON m.id = mma.member_id
        INNER JOIN medebe meb ON mma.medebe_id = meb.id
        GROUP BY m.section_name
    """)
    section_stats = cursor.fetchall()
    
    # Chart data for distribution
    cursor.execute("""
        SELECT meb.medebe_name, m.section_name, COUNT(mma.id) as count
        FROM medebe meb
        INNER JOIN member_medebe_assignment mma ON meb.id = mma.medebe_id
        INNER JOIN member_registration m ON mma.member_id = m.id
        GROUP BY meb.medebe_name, m.section_name
        ORDER BY m.section_name, meb.medebe_name
    """)
    chart_data = cursor.fetchall()
    
    sections = ['የሕፃናት ክፍል', 'ማህከላዊያን ክፍል', 'ወጣት ክፍል', 'ወላጅ ክፍል']
    
    cursor.close()
    conn.close()
    
    return render_template('member_medebe_report.html',
                         member_assignments=member_assignments,
                         medebes=medebes,
                         section_stats=section_stats,
                         chart_data=chart_data,
                         sections=sections,
                         section_filter=section_filter,
                         medebe_filter=medebe_filter)

if __name__ == '__main__':
    # Initialize database and tables
    initialize_app()
    
    # Run the Flask application
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )

