"""
Donation Management Module
Handles donation types, settings, records, and Chapa payment integration
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from database import get_db_connection
from auth import login_required, role_required
from datetime import datetime
import json
import requests
import uuid
from decimal import Decimal
import os
from config import Config

# Create donation management blueprint
donation_management = Blueprint('donation_management', __name__, url_prefix='/admin/donation')

# Helper function to get donation setting (with environment variable fallback)
def get_donation_setting(key, default=''):
    """Get a donation setting value from database, with environment variable fallback for security"""
    # Check environment variables first for sensitive keys
    if key == 'chapa_secret_key':
        env_value = os.environ.get('CHAPA_SECRET_KEY') or Config.CHAPA_SECRET_KEY
        if env_value:
            return env_value
    elif key == 'chapa_public_key':
        env_value = os.environ.get('CHAPA_PUBLIC_KEY') or Config.CHAPA_PUBLIC_KEY
        if env_value:
            return env_value
    
    # Fallback to database
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT setting_value FROM donation_settings WHERE setting_key = %s", (key,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else default
    except:
        return default

# Helper function to update donation setting
def update_donation_setting(key, value, updated_by='ADMIN'):
    """Update a donation setting value"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO donation_settings (setting_key, setting_value, updated_by)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                setting_value = VALUES(setting_value),
                updated_by = VALUES(updated_by),
                updated_at = CURRENT_TIMESTAMP
        """, (key, value, updated_by))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating setting {key}: {str(e)}")
        return False

# ========================================
# DONATION TYPE MANAGEMENT
# ========================================

@donation_management.route('/types')
@login_required
@role_required('Super Admin', 'Admin')
def manage_donation_types():
    """List all donation types"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM donation_types 
            ORDER BY created_at DESC
        """)
        types = cursor.fetchall()
    except Exception as e:
        types = []
        flash(f'Error loading donation types: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/donation/types.html', types=types)

@donation_management.route('/types/add', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def add_donation_type():
    """Add new donation type"""
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            name = request.form.get('name', '').strip()
            name_amharic = request.form.get('name_amharic', '').strip()
            description = request.form.get('description', '').strip()
            description_amharic = request.form.get('description_amharic', '').strip()
            is_active = 1 if request.form.get('is_active') else 0
            
            if not name:
                flash('Donation type name is required', 'error')
                return render_template('admin/donation/type_form.html')
            
            cursor.execute("""
                INSERT INTO donation_types (name, name_amharic, description, description_amharic, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, name_amharic, description, description_amharic, is_active, session.get('payroll_number', 'ADMIN')))
            
            conn.commit()
            flash('Donation type added successfully!', 'success')
            return redirect(url_for('donation_management.manage_donation_types'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error adding donation type: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('admin/donation/type_form.html')

@donation_management.route('/types/edit/<int:type_id>', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def edit_donation_type(type_id):
    """Edit donation type"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            name_amharic = request.form.get('name_amharic', '').strip()
            description = request.form.get('description', '').strip()
            description_amharic = request.form.get('description_amharic', '').strip()
            is_active = 1 if request.form.get('is_active') else 0
            
            if not name:
                flash('Donation type name is required', 'error')
                cursor.execute("SELECT * FROM donation_types WHERE id = %s", (type_id,))
                donation_type = cursor.fetchone()
                cursor.close()
                conn.close()
                return render_template('admin/donation/type_form.html', donation_type=donation_type)
            
            cursor.execute("""
                UPDATE donation_types SET
                name=%s, name_amharic=%s, description=%s, description_amharic=%s, is_active=%s
                WHERE id=%s
            """, (name, name_amharic, description, description_amharic, is_active, type_id))
            
            conn.commit()
            flash('Donation type updated successfully!', 'success')
            return redirect(url_for('donation_management.manage_donation_types'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error updating donation type: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    try:
        cursor.execute("SELECT * FROM donation_types WHERE id = %s", (type_id,))
        donation_type = cursor.fetchone()
    except Exception as e:
        flash(f'Error loading donation type: {str(e)}', 'error')
        donation_type = None
    finally:
        cursor.close()
        conn.close()
    
    if not donation_type:
        flash('Donation type not found', 'error')
        return redirect(url_for('donation_management.manage_donation_types'))
    
    return render_template('admin/donation/type_form.html', donation_type=donation_type)

@donation_management.route('/types/delete/<int:type_id>', methods=['POST'])
@login_required
@role_required('Super Admin', 'Admin')
def delete_donation_type(type_id):
    """Delete donation type"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM donation_types WHERE id = %s", (type_id,))
        conn.commit()
        flash('Donation type deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting donation type: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('donation_management.manage_donation_types'))

@donation_management.route('/types/toggle/<int:type_id>', methods=['POST'])
@login_required
@role_required('Super Admin', 'Admin')
def toggle_donation_type(type_id):
    """Toggle donation type status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE donation_types SET is_active = NOT is_active WHERE id = %s", (type_id,))
        conn.commit()
        flash('Donation type status updated!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('donation_management.manage_donation_types'))

# ========================================
# DONATION SETTINGS
# ========================================

@donation_management.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def donation_settings():
    """Manage donation settings"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    if request.method == 'POST':
        try:
            # Get all form values
            settings = {
                'chapa_public_key': request.form.get('chapa_public_key', ''),
                'chapa_secret_key': request.form.get('chapa_secret_key', ''),
                'default_currency': request.form.get('default_currency', 'ETB'),
                'allow_any_amount': '1' if request.form.get('allow_any_amount') else '0',
                'min_donation_amount': request.form.get('min_donation_amount', '10'),
                'max_donation_amount': request.form.get('max_donation_amount', '1000000'),
                'donation_module_enabled': '1' if request.form.get('donation_module_enabled') else '0',
                'thank_you_message': request.form.get('thank_you_message', ''),
                'thank_you_message_amharic': request.form.get('thank_you_message_amharic', ''),
                'redirect_url_after_payment': request.form.get('redirect_url_after_payment', '/donation/thank-you'),
                'callback_url': request.form.get('callback_url', '')
            }
            
            # Update all settings
            for key, value in settings.items():
                update_donation_setting(key, value, session.get('payroll_number', 'ADMIN'))
            
            flash('Donation settings updated successfully!', 'success')
            return redirect(url_for('donation_management.donation_settings'))
            
        except Exception as e:
            flash(f'Error updating settings: {str(e)}', 'error')
    
    # Get all settings
    try:
        cursor.execute("SELECT setting_key, setting_value FROM donation_settings")
        settings_dict = {row['setting_key']: row['setting_value'] for row in cursor.fetchall()}
    except Exception as e:
        settings_dict = {}
        flash(f'Error loading settings: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/donation/settings.html', settings=settings_dict)

# ========================================
# DONATION RECORDS
# ========================================

@donation_management.route('/records')
@login_required
@role_required('Super Admin', 'Admin')
def donation_records():
    """View all donation records"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        # Get filters
        status_filter = request.args.get('status', '')
        type_filter = request.args.get('type', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Build query (use donations table, fallback to donation_records for compatibility)
        query = """
            SELECT d.*, dt.name as donation_type_name, dt.name_amharic as donation_type_name_amharic
            FROM donations d
            LEFT JOIN donation_types dt ON d.donation_type_id = dt.id
            WHERE 1=1
        """
        params = []
        
        if status_filter:
            query += " AND d.payment_status = %s"
            params.append(status_filter)
        
        if type_filter:
            query += " AND d.donation_type_id = %s"
            params.append(type_filter)
        
        if date_from:
            query += " AND DATE(d.created_at) >= %s"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(d.created_at) <= %s"
            params.append(date_to)
        
        query += " ORDER BY d.created_at DESC LIMIT 1000"
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        # Get donation types for filter
        cursor.execute("SELECT id, name, name_amharic FROM donation_types WHERE is_active = 1 ORDER BY name")
        donation_types = cursor.fetchall()
        
    except Exception as e:
        records = []
        donation_types = []
        flash(f'Error loading donation records: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/donation/records.html', 
                         records=records, 
                         donation_types=donation_types,
                         status_filter=status_filter,
                         type_filter=type_filter,
                         date_from=date_from,
                         date_to=date_to)

@donation_management.route('/records/<int:record_id>')
@login_required
@role_required('Super Admin', 'Admin')
def view_donation_record(record_id):
    """View donation record details"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT d.*, dt.name as donation_type_name, dt.name_amharic as donation_type_name_amharic
            FROM donations d
            LEFT JOIN donation_types dt ON d.donation_type_id = dt.id
            WHERE d.id = %s
        """, (record_id,))
        record = cursor.fetchone()
    except Exception as e:
        record = None
        flash(f'Error loading donation record: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    if not record:
        flash('Donation record not found', 'error')
        return redirect(url_for('donation_management.donation_records'))
    
    return render_template('admin/donation/record_view.html', record=record)

@donation_management.route('/records/<int:record_id>/mark-completed', methods=['POST'])
@login_required
@role_required('Super Admin', 'Admin')
def mark_donation_completed(record_id):
    """Mark a donation as completed"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE donations 
            SET payment_status = 'Completed', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (record_id,))
        conn.commit()
        flash('Donation marked as completed successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error updating donation: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('donation_management.donation_records'))

@donation_management.route('/records/export')
@login_required
@role_required('Super Admin', 'Admin')
def export_donation_records():
    """Export donation records to Excel/PDF"""
    format_type = request.args.get('format', 'excel')
    # Implementation for export will be added
    flash('Export feature coming soon', 'info')
    return redirect(url_for('donation_management.donation_records'))

