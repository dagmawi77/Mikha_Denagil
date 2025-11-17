"""
Public Website Routes
Modern, responsive public-facing website for Mikha Denagil Spiritual Society
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from database import get_db_connection

# Create public website blueprint
public_website = Blueprint('public_website', __name__)

@public_website.route('/')
def homepage():
    """Public homepage with hero slider, about, services, gallery, etc."""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        # Get active hero slides
        cursor.execute("""
            SELECT * FROM public_hero_slides 
            WHERE is_active = 1 
            ORDER BY display_order ASC
        """)
        hero_slides = cursor.fetchall()
        
        # Get active services (limit to 6 for homepage)
        cursor.execute("""
            SELECT * FROM public_services 
            WHERE is_active = 1 
            ORDER BY display_order ASC 
            LIMIT 6
        """)
        services = cursor.fetchall()
        
        # Get featured gallery photos
        cursor.execute("""
            SELECT * FROM public_gallery 
            WHERE is_active = 1 AND is_featured = 1 
            ORDER BY display_order ASC 
            LIMIT 12
        """)
        gallery_photos = cursor.fetchall()
        
        # Get about section content
        cursor.execute("""
            SELECT * FROM public_about_content 
            WHERE section_name = 'homepage_intro' AND is_active = 1
        """)
        about_intro = cursor.fetchone()
        
        # Get public announcements
        cursor.execute("""
            SELECT pa.*, p.post_title, p.post_content, p.post_type, p.created_at
            FROM public_announcements pa
            JOIN posts p ON pa.post_id = p.id
            WHERE pa.is_active = 1 AND pa.display_on_homepage = 1 AND p.status = 'Active'
            ORDER BY pa.display_order ASC, p.created_at DESC
            LIMIT 5
        """)
        announcements = cursor.fetchall()
        
    except Exception as e:
        hero_slides = []
        services = []
        gallery_photos = []
        about_intro = None
        announcements = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/homepage.html',
                         hero_slides=hero_slides,
                         services=services,
                         gallery_photos=gallery_photos,
                         about_intro=about_intro,
                         announcements=announcements)

@public_website.route('/about')
def about_page():
    """Full About page with mission, vision, leadership"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        # Get all about sections
        cursor.execute("""
            SELECT * FROM public_about_content 
            WHERE is_active = 1 
            ORDER BY display_order ASC
        """)
        about_sections = cursor.fetchall()
        
        # Get leadership/committee members (if stored in member_positions or separate table)
        # For now, we'll use about_content with section_name = 'leadership'
        cursor.execute("""
            SELECT * FROM public_about_content 
            WHERE section_name LIKE 'leadership%' AND is_active = 1 
            ORDER BY display_order ASC
        """)
        leadership = cursor.fetchall()
        
    except Exception as e:
        about_sections = []
        leadership = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/about.html',
                         about_sections=about_sections,
                         leadership=leadership)

@public_website.route('/history')
def history_page():
    """History page with timeline"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM public_history_timeline 
            WHERE is_active = 1 
            ORDER BY year ASC, display_order ASC
        """)
        timeline_events = cursor.fetchall()
    except Exception as e:
        timeline_events = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/history.html', timeline_events=timeline_events)

@public_website.route('/services')
def services_page():
    """Services page listing all services"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM public_services 
            WHERE is_active = 1 
            ORDER BY display_order ASC
        """)
        services = cursor.fetchall()
    except Exception as e:
        services = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/services.html', services=services)

@public_website.route('/services/<int:service_id>')
def service_detail(service_id):
    """Individual service detail page"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM public_services 
            WHERE id = %s AND is_active = 1
        """, (service_id,))
        service = cursor.fetchone()
        
        if not service:
            flash('Service not found', 'error')
            return redirect(url_for('public_website.services_page'))
    except Exception as e:
        flash('Error loading service', 'error')
        return redirect(url_for('public_website.services_page'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/service_detail.html', service=service)

@public_website.route('/donation')
def donation_page():
    """Donation page with payment methods"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT * FROM public_donation_info 
            WHERE is_active = 1 
            ORDER BY display_order ASC
        """)
        donation_methods = cursor.fetchall()
        
        # Get donation message
        cursor.execute("""
            SELECT * FROM public_about_content 
            WHERE section_name = 'donation_message' AND is_active = 1
        """)
        donation_message = cursor.fetchone()
    except Exception as e:
        donation_methods = []
        donation_message = None
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/donation.html',
                         donation_methods=donation_methods,
                         donation_message=donation_message)

@public_website.route('/gallery')
def gallery_page():
    """Gallery page with photo grid"""
    category = request.args.get('category', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        # Get all categories
        cursor.execute("""
            SELECT DISTINCT category, category_amharic 
            FROM public_gallery 
            WHERE is_active = 1 
            ORDER BY category
        """)
        categories = cursor.fetchall()
        
        # Get photos (filtered by category if provided)
        if category:
            cursor.execute("""
                SELECT * FROM public_gallery 
                WHERE is_active = 1 AND category = %s 
                ORDER BY display_order ASC, created_at DESC
            """, (category,))
        else:
            cursor.execute("""
                SELECT * FROM public_gallery 
                WHERE is_active = 1 
                ORDER BY display_order ASC, created_at DESC
            """)
        photos = cursor.fetchall()
    except Exception as e:
        categories = []
        photos = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/gallery.html',
                         photos=photos,
                         categories=categories,
                         selected_category=category)

@public_website.route('/contact', methods=['GET', 'POST'])
def contact_page():
    """Contact page with form and information"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        # Get contact information
        cursor.execute("""
            SELECT * FROM public_contact_info 
            WHERE is_active = 1 
            ORDER BY display_order ASC
        """)
        contact_info = cursor.fetchall()
        
        if request.method == 'POST':
            # Handle contact form submission
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            subject = request.form.get('subject', '').strip()
            message = request.form.get('message', '').strip()
            
            if not name or not message:
                flash('Name and message are required', 'error')
                return render_template('public/contact.html', contact_info=contact_info)
            
            # Insert submission
            cursor.execute("""
                INSERT INTO public_contact_submissions 
                (name, email, phone, subject, message, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, email, phone, subject, message, request.remote_addr))
            
            conn.commit()
            flash('Thank you for your message! We will get back to you soon.', 'success')
            return redirect(url_for('public_website.contact_page'))
            
    except Exception as e:
        if request.method == 'POST':
            conn.rollback()
            flash('Error submitting message. Please try again.', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/contact.html', contact_info=contact_info)

@public_website.route('/announcements')
def announcements_page():
    """Public announcements page"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT pa.*, p.post_title, p.post_content, p.post_type, 
                   p.created_at, p.attachment_path, p.attachment_name
            FROM public_announcements pa
            JOIN posts p ON pa.post_id = p.id
            WHERE pa.is_active = 1 AND p.status = 'Active'
            ORDER BY pa.display_order ASC, p.created_at DESC
        """)
        announcements = cursor.fetchall()
    except Exception as e:
        announcements = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/announcements.html', announcements=announcements)

# Export blueprint
__all__ = ['public_website']

