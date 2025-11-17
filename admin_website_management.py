"""
Admin Routes for Public Website Content Management
Allows non-technical staff to manage website content from admin dashboard
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from database import get_db_connection
from auth import login_required, role_required
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from config import Config

# Create admin website management blueprint
admin_website = Blueprint('admin_website', __name__, url_prefix='/admin/website')

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def save_uploaded_file(file, subfolder='website'):
    """Save uploaded file and return path"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = str(int(datetime.now().timestamp()))
        filename = f"{timestamp}_{filename}"
        upload_path = os.path.join(Config.UPLOAD_FOLDER, subfolder)
        os.makedirs(upload_path, exist_ok=True)
        filepath = os.path.join(upload_path, filename)
        file.save(filepath)
        return os.path.join('uploads', subfolder, filename).replace('\\', '/')
    return None

# ========================================
# HERO SLIDES MANAGEMENT
# ========================================

@admin_website.route('/hero-slides')
@login_required
@role_required('Super Admin', 'Admin')
def manage_hero_slides():
    """List all hero slides"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM public_hero_slides 
            ORDER BY display_order ASC, created_at DESC
        """)
        slides = cursor.fetchall()
    except Exception as e:
        slides = []
        flash(f'Error loading slides: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/hero_slides.html', slides=slides)

@admin_website.route('/hero-slides/add', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def add_hero_slide():
    """Add new hero slide"""
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            title = request.form.get('title', '').strip()
            title_amharic = request.form.get('title_amharic', '').strip()
            description = request.form.get('description', '').strip()
            description_amharic = request.form.get('description_amharic', '').strip()
            button_text = request.form.get('button_text', 'Learn More').strip()
            button_link = request.form.get('button_link', '').strip()
            display_order = int(request.form.get('display_order', 0))
            is_active = 1 if request.form.get('is_active') else 0
            
            # Handle image upload
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    image_path = save_uploaded_file(file, 'hero_slides')
            
            if not title or not image_path:
                flash('Title and image are required', 'error')
                return render_template('admin/website/hero_slide_form.html')
            
            cursor.execute("""
                INSERT INTO public_hero_slides 
                (title, title_amharic, description, description_amharic, image_path,
                 button_text, button_link, display_order, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (title, title_amharic, description, description_amharic, image_path,
                  button_text, button_link, display_order, is_active, session.get('user_id', 'ADMIN')))
            
            conn.commit()
            flash('Hero slide added successfully!', 'success')
            return redirect(url_for('admin_website.manage_hero_slides'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error adding slide: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('admin/website/hero_slide_form.html')

@admin_website.route('/hero-slides/<int:slide_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def edit_hero_slide(slide_id):
    """Edit hero slide"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            title_amharic = request.form.get('title_amharic', '').strip()
            description = request.form.get('description', '').strip()
            description_amharic = request.form.get('description_amharic', '').strip()
            button_text = request.form.get('button_text', 'Learn More').strip()
            button_link = request.form.get('button_link', '').strip()
            display_order = int(request.form.get('display_order', 0))
            is_active = 1 if request.form.get('is_active') else 0
            
            # Handle image upload (optional - keep existing if not provided)
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    image_path = save_uploaded_file(file, 'hero_slides')
            
            if image_path:
                cursor.execute("""
                    UPDATE public_hero_slides SET
                    title=%s, title_amharic=%s, description=%s, description_amharic=%s,
                    image_path=%s, button_text=%s, button_link=%s, display_order=%s, is_active=%s
                    WHERE id=%s
                """, (title, title_amharic, description, description_amharic, image_path,
                      button_text, button_link, display_order, is_active, slide_id))
            else:
                cursor.execute("""
                    UPDATE public_hero_slides SET
                    title=%s, title_amharic=%s, description=%s, description_amharic=%s,
                    button_text=%s, button_link=%s, display_order=%s, is_active=%s
                    WHERE id=%s
                """, (title, title_amharic, description, description_amharic,
                      button_text, button_link, display_order, is_active, slide_id))
            
            conn.commit()
            flash('Hero slide updated successfully!', 'success')
            return redirect(url_for('admin_website.manage_hero_slides'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error updating slide: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    try:
        cursor.execute("SELECT * FROM public_hero_slides WHERE id = %s", (slide_id,))
        slide = cursor.fetchone()
        if not slide:
            flash('Slide not found', 'error')
            return redirect(url_for('admin_website.manage_hero_slides'))
    except Exception as e:
        flash(f'Error loading slide: {str(e)}', 'error')
        return redirect(url_for('admin_website.manage_hero_slides'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/hero_slide_form.html', slide=slide)

@admin_website.route('/hero-slides/<int:slide_id>/delete', methods=['POST'])
@login_required
@role_required('Super Admin', 'Admin')
def delete_hero_slide(slide_id):
    """Delete hero slide"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM public_hero_slides WHERE id = %s", (slide_id,))
        conn.commit()
        flash('Hero slide deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting slide: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_website.manage_hero_slides'))

# ========================================
# SERVICES MANAGEMENT
# ========================================

@admin_website.route('/services')
@login_required
@role_required('Super Admin', 'Admin')
def manage_services():
    """List all services"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM public_services 
            ORDER BY display_order ASC, created_at DESC
        """)
        services = cursor.fetchall()
    except Exception as e:
        services = []
        flash(f'Error loading services: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/services.html', services=services)

@admin_website.route('/services/add', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def add_service():
    """Add new service"""
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            service_name = request.form.get('service_name', '').strip()
            service_name_amharic = request.form.get('service_name_amharic', '').strip()
            icon_class = request.form.get('icon_class', '').strip()
            short_description = request.form.get('short_description', '').strip()
            full_description = request.form.get('full_description', '').strip()
            description_amharic = request.form.get('description_amharic', '').strip()
            display_order = int(request.form.get('display_order', 0))
            is_active = 1 if request.form.get('is_active') else 0
            
            # Handle image upload
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    image_path = save_uploaded_file(file, 'services')
            
            if not service_name:
                flash('Service name is required', 'error')
                return render_template('admin/website/service_form.html')
            
            cursor.execute("""
                INSERT INTO public_services 
                (service_name, service_name_amharic, icon_class, short_description,
                 full_description, description_amharic, image_path, display_order, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (service_name, service_name_amharic, icon_class, short_description,
                  full_description, description_amharic, image_path, display_order, is_active,
                  session.get('user_id', 'ADMIN')))
            
            conn.commit()
            flash('Service added successfully!', 'success')
            return redirect(url_for('admin_website.manage_services'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error adding service: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('admin/website/service_form.html')

@admin_website.route('/services/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def edit_service(service_id):
    """Edit service"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    if request.method == 'POST':
        try:
            service_name = request.form.get('service_name', '').strip()
            service_name_amharic = request.form.get('service_name_amharic', '').strip()
            icon_class = request.form.get('icon_class', '').strip()
            short_description = request.form.get('short_description', '').strip()
            full_description = request.form.get('full_description', '').strip()
            description_amharic = request.form.get('description_amharic', '').strip()
            display_order = int(request.form.get('display_order', 0))
            is_active = 1 if request.form.get('is_active') else 0
            
            # Handle image upload (optional)
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    image_path = save_uploaded_file(file, 'services')
            
            if image_path:
                cursor.execute("""
                    UPDATE public_services SET
                    service_name=%s, service_name_amharic=%s, icon_class=%s,
                    short_description=%s, full_description=%s, description_amharic=%s,
                    image_path=%s, display_order=%s, is_active=%s
                    WHERE id=%s
                """, (service_name, service_name_amharic, icon_class, short_description,
                      full_description, description_amharic, image_path, display_order, is_active, service_id))
            else:
                cursor.execute("""
                    UPDATE public_services SET
                    service_name=%s, service_name_amharic=%s, icon_class=%s,
                    short_description=%s, full_description=%s, description_amharic=%s,
                    display_order=%s, is_active=%s
                    WHERE id=%s
                """, (service_name, service_name_amharic, icon_class, short_description,
                      full_description, description_amharic, display_order, is_active, service_id))
            
            conn.commit()
            flash('Service updated successfully!', 'success')
            return redirect(url_for('admin_website.manage_services'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error updating service: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    try:
        cursor.execute("SELECT * FROM public_services WHERE id = %s", (service_id,))
        service = cursor.fetchone()
        if not service:
            flash('Service not found', 'error')
            return redirect(url_for('admin_website.manage_services'))
    except Exception as e:
        flash(f'Error loading service: {str(e)}', 'error')
        return redirect(url_for('admin_website.manage_services'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/service_form.html', service=service)

@admin_website.route('/services/<int:service_id>/delete', methods=['POST'])
@login_required
@role_required('Super Admin', 'Admin')
def delete_service(service_id):
    """Delete service"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM public_services WHERE id = %s", (service_id,))
        conn.commit()
        flash('Service deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting service: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_website.manage_services'))

# ========================================
# GALLERY MANAGEMENT
# ========================================

@admin_website.route('/gallery')
@login_required
@role_required('Super Admin', 'Admin')
def manage_gallery():
    """List all gallery photos"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM public_gallery 
            ORDER BY display_order ASC, created_at DESC
        """)
        photos = cursor.fetchall()
    except Exception as e:
        photos = []
        flash(f'Error loading gallery: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/gallery.html', photos=photos)

@admin_website.route('/gallery/add', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def add_gallery_photo():
    """Add new gallery photo"""
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            title = request.form.get('title', '').strip()
            title_amharic = request.form.get('title_amharic', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'General').strip()
            category_amharic = request.form.get('category_amharic', '').strip()
            display_order = int(request.form.get('display_order', 0))
            is_featured = 1 if request.form.get('is_featured') else 0
            is_active = 1 if request.form.get('is_active') else 0
            
            # Handle image upload
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    image_path = save_uploaded_file(file, 'gallery')
            
            if not image_path:
                flash('Image is required', 'error')
                return render_template('admin/website/gallery_form.html')
            
            cursor.execute("""
                INSERT INTO public_gallery 
                (title, title_amharic, description, image_path, category, category_amharic,
                 display_order, is_featured, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (title, title_amharic, description, image_path, category, category_amharic,
                  display_order, is_featured, is_active, session.get('user_id', 'ADMIN')))
            
            conn.commit()
            flash('Photo added successfully!', 'success')
            return redirect(url_for('admin_website.manage_gallery'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error adding photo: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('admin/website/gallery_form.html')

@admin_website.route('/gallery/<int:photo_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def edit_gallery_photo(photo_id):
    """Edit gallery photo"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            title_amharic = request.form.get('title_amharic', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'General').strip()
            category_amharic = request.form.get('category_amharic', '').strip()
            display_order = int(request.form.get('display_order', 0))
            is_featured = 1 if request.form.get('is_featured') else 0
            is_active = 1 if request.form.get('is_active') else 0
            
            # Handle image upload (optional)
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    image_path = save_uploaded_file(file, 'gallery')
            
            if image_path:
                cursor.execute("""
                    UPDATE public_gallery SET
                    title=%s, title_amharic=%s, description=%s, category=%s, category_amharic=%s,
                    image_path=%s, display_order=%s, is_featured=%s, is_active=%s
                    WHERE id=%s
                """, (title, title_amharic, description, category, category_amharic,
                      image_path, display_order, is_featured, is_active, photo_id))
            else:
                cursor.execute("""
                    UPDATE public_gallery SET
                    title=%s, title_amharic=%s, description=%s, category=%s, category_amharic=%s,
                    display_order=%s, is_featured=%s, is_active=%s
                    WHERE id=%s
                """, (title, title_amharic, description, category, category_amharic,
                      display_order, is_featured, is_active, photo_id))
            
            conn.commit()
            flash('Photo updated successfully!', 'success')
            return redirect(url_for('admin_website.manage_gallery'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error updating photo: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    try:
        cursor.execute("SELECT * FROM public_gallery WHERE id = %s", (photo_id,))
        photo = cursor.fetchone()
        if not photo:
            flash('Photo not found', 'error')
            return redirect(url_for('admin_website.manage_gallery'))
    except Exception as e:
        flash(f'Error loading photo: {str(e)}', 'error')
        return redirect(url_for('admin_website.manage_gallery'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/gallery_form.html', photo=photo)

@admin_website.route('/gallery/<int:photo_id>/delete', methods=['POST'])
@login_required
@role_required('Super Admin', 'Admin')
def delete_gallery_photo(photo_id):
    """Delete gallery photo"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM public_gallery WHERE id = %s", (photo_id,))
        conn.commit()
        flash('Photo deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting photo: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_website.manage_gallery'))

# ========================================
# DONATION INFO MANAGEMENT
# ========================================

@admin_website.route('/donation')
@login_required
@role_required('Super Admin', 'Admin')
def manage_donation_info():
    """List all donation methods"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM public_donation_info 
            ORDER BY display_order ASC, created_at DESC
        """)
        donation_methods = cursor.fetchall()
    except Exception as e:
        donation_methods = []
        flash(f'Error loading donation info: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/donation_info.html', donation_methods=donation_methods)

@admin_website.route('/donation/add', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def add_donation_method():
    """Add new donation method"""
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            donation_method = request.form.get('donation_method', '').strip()
            method_name_amharic = request.form.get('method_name_amharic', '').strip()
            account_name = request.form.get('account_name', '').strip()
            account_number = request.form.get('account_number', '').strip()
            bank_name = request.form.get('bank_name', '').strip()
            instructions = request.form.get('instructions', '').strip()
            instructions_amharic = request.form.get('instructions_amharic', '').strip()
            display_order = int(request.form.get('display_order', 0))
            is_active = 1 if request.form.get('is_active') else 0
            
            # Handle QR code upload
            qr_code_image = None
            if 'qr_code_image' in request.files:
                file = request.files['qr_code_image']
                if file and file.filename:
                    qr_code_image = save_uploaded_file(file, 'donation_qr')
            
            if not donation_method:
                flash('Donation method name is required', 'error')
                return render_template('admin/website/donation_form.html')
            
            cursor.execute("""
                INSERT INTO public_donation_info 
                (donation_method, method_name_amharic, account_name, account_number,
                 bank_name, qr_code_image, instructions, instructions_amharic,
                 display_order, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (donation_method, method_name_amharic, account_name, account_number,
                  bank_name, qr_code_image, instructions, instructions_amharic,
                  display_order, is_active, session.get('user_id', 'ADMIN')))
            
            conn.commit()
            flash('Donation method added successfully!', 'success')
            return redirect(url_for('admin_website.manage_donation_info'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error adding donation method: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('admin/website/donation_form.html')

@admin_website.route('/donation/<int:method_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def edit_donation_method(method_id):
    """Edit donation method"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    if request.method == 'POST':
        try:
            donation_method = request.form.get('donation_method', '').strip()
            method_name_amharic = request.form.get('method_name_amharic', '').strip()
            account_name = request.form.get('account_name', '').strip()
            account_number = request.form.get('account_number', '').strip()
            bank_name = request.form.get('bank_name', '').strip()
            instructions = request.form.get('instructions', '').strip()
            instructions_amharic = request.form.get('instructions_amharic', '').strip()
            display_order = int(request.form.get('display_order', 0))
            is_active = 1 if request.form.get('is_active') else 0
            
            # Handle QR code upload (optional)
            qr_code_image = None
            if 'qr_code_image' in request.files:
                file = request.files['qr_code_image']
                if file and file.filename:
                    qr_code_image = save_uploaded_file(file, 'donation_qr')
            
            if qr_code_image:
                cursor.execute("""
                    UPDATE public_donation_info SET
                    donation_method=%s, method_name_amharic=%s, account_name=%s,
                    account_number=%s, bank_name=%s, qr_code_image=%s,
                    instructions=%s, instructions_amharic=%s, display_order=%s, is_active=%s
                    WHERE id=%s
                """, (donation_method, method_name_amharic, account_name, account_number,
                      bank_name, qr_code_image, instructions, instructions_amharic,
                      display_order, is_active, method_id))
            else:
                cursor.execute("""
                    UPDATE public_donation_info SET
                    donation_method=%s, method_name_amharic=%s, account_name=%s,
                    account_number=%s, bank_name=%s, instructions=%s, instructions_amharic=%s,
                    display_order=%s, is_active=%s
                    WHERE id=%s
                """, (donation_method, method_name_amharic, account_name, account_number,
                      bank_name, instructions, instructions_amharic, display_order, is_active, method_id))
            
            conn.commit()
            flash('Donation method updated successfully!', 'success')
            return redirect(url_for('admin_website.manage_donation_info'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error updating donation method: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    try:
        cursor.execute("SELECT * FROM public_donation_info WHERE id = %s", (method_id,))
        method = cursor.fetchone()
        if not method:
            flash('Donation method not found', 'error')
            return redirect(url_for('admin_website.manage_donation_info'))
    except Exception as e:
        flash(f'Error loading donation method: {str(e)}', 'error')
        return redirect(url_for('admin_website.manage_donation_info'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/donation_form.html', method=method)

@admin_website.route('/donation/<int:method_id>/delete', methods=['POST'])
@login_required
@role_required('Super Admin', 'Admin')
def delete_donation_method(method_id):
    """Delete donation method"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM public_donation_info WHERE id = %s", (method_id,))
        conn.commit()
        flash('Donation method deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting donation method: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_website.manage_donation_info'))

# ========================================
# CONTACT INFO MANAGEMENT
# ========================================

@admin_website.route('/contact')
@login_required
@role_required('Super Admin', 'Admin')
def manage_contact_info():
    """List all contact information"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM public_contact_info 
            ORDER BY display_order ASC
        """)
        contact_info = cursor.fetchall()
    except Exception as e:
        contact_info = []
        flash(f'Error loading contact info: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/contact_info.html', contact_info=contact_info)

@admin_website.route('/contact/add', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def add_contact_info():
    """Add new contact information"""
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            contact_type = request.form.get('contact_type', '').strip()
            label = request.form.get('label', '').strip()
            label_amharic = request.form.get('label_amharic', '').strip()
            value = request.form.get('value', '').strip()
            icon_class = request.form.get('icon_class', '').strip()
            display_order = int(request.form.get('display_order', 0))
            is_active = 1 if request.form.get('is_active') else 0
            
            if not contact_type or not value:
                flash('Contact type and value are required', 'error')
                return render_template('admin/website/contact_form.html')
            
            cursor.execute("""
                INSERT INTO public_contact_info 
                (contact_type, label, label_amharic, value, icon_class, display_order, is_active, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (contact_type, label, label_amharic, value, icon_class, display_order, is_active,
                  session.get('user_id', 'ADMIN')))
            
            conn.commit()
            flash('Contact information added successfully!', 'success')
            return redirect(url_for('admin_website.manage_contact_info'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error adding contact info: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('admin/website/contact_form.html')

@admin_website.route('/contact/<int:contact_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Super Admin', 'Admin')
def edit_contact_info(contact_id):
    """Edit contact information"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    if request.method == 'POST':
        try:
            contact_type = request.form.get('contact_type', '').strip()
            label = request.form.get('label', '').strip()
            label_amharic = request.form.get('label_amharic', '').strip()
            value = request.form.get('value', '').strip()
            icon_class = request.form.get('icon_class', '').strip()
            display_order = int(request.form.get('display_order', 0))
            is_active = 1 if request.form.get('is_active') else 0
            
            cursor.execute("""
                UPDATE public_contact_info SET
                contact_type=%s, label=%s, label_amharic=%s, value=%s,
                icon_class=%s, display_order=%s, is_active=%s, updated_by=%s
                WHERE id=%s
            """, (contact_type, label, label_amharic, value, icon_class, display_order, is_active,
                  session.get('user_id', 'ADMIN'), contact_id))
            
            conn.commit()
            flash('Contact information updated successfully!', 'success')
            return redirect(url_for('admin_website.manage_contact_info'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error updating contact info: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    try:
        cursor.execute("SELECT * FROM public_contact_info WHERE id = %s", (contact_id,))
        contact = cursor.fetchone()
        if not contact:
            flash('Contact information not found', 'error')
            return redirect(url_for('admin_website.manage_contact_info'))
    except Exception as e:
        flash(f'Error loading contact info: {str(e)}', 'error')
        return redirect(url_for('admin_website.manage_contact_info'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/contact_form.html', contact=contact)

@admin_website.route('/contact/<int:contact_id>/delete', methods=['POST'])
@login_required
@role_required('Super Admin', 'Admin')
def delete_contact_info(contact_id):
    """Delete contact information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM public_contact_info WHERE id = %s", (contact_id,))
        conn.commit()
        flash('Contact information deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting contact info: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_website.manage_contact_info'))

# ========================================
# CONTACT SUBMISSIONS MANAGEMENT
# ========================================

@admin_website.route('/contact-submissions')
@login_required
@role_required('Super Admin', 'Admin')
def manage_contact_submissions():
    """List all contact form submissions"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM public_contact_submissions 
            ORDER BY created_at DESC
        """)
        submissions = cursor.fetchall()
    except Exception as e:
        submissions = []
        flash(f'Error loading submissions: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/contact_submissions.html', submissions=submissions)

@admin_website.route('/contact-submissions/<int:submission_id>/view')
@login_required
@role_required('Super Admin', 'Admin')
def view_contact_submission(submission_id):
    """View contact submission details"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM public_contact_submissions WHERE id = %s", (submission_id,))
        submission = cursor.fetchone()
        
        if not submission:
            flash('Submission not found', 'error')
            return redirect(url_for('admin_website.manage_contact_submissions'))
        
        # Mark as read
        if submission['status'] == 'New':
            cursor.execute("""
                UPDATE public_contact_submissions 
                SET status='Read', read_at=NOW(), read_by=%s
                WHERE id=%s
            """, (session.get('user_id', 'ADMIN'), submission_id))
            conn.commit()
        
    except Exception as e:
        flash(f'Error loading submission: {str(e)}', 'error')
        return redirect(url_for('admin_website.manage_contact_submissions'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin/website/contact_submission_view.html', submission=submission)

# Export blueprint
__all__ = ['admin_website']

