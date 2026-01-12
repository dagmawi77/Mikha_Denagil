"""
Public Website Routes
Modern, responsive public-facing website for Mikha Denagil Spiritual Society
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
from database import get_db_connection
from datetime import datetime
import json
import requests
import uuid
from decimal import Decimal
import os
from config import Config

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
            SELECT id, title, title_amharic, description, description_amharic, 
                   image_path, button_text, button_link, display_order, is_active
            FROM public_hero_slides 
            WHERE is_active = 1 
            ORDER BY display_order ASC
        """)
        hero_slides = cursor.fetchall()
        
        # Debug: Print slides count and check image_path
        print(f"[Homepage] Loaded {len(hero_slides)} active hero slides")
        for idx, slide in enumerate(hero_slides):
            # Handle both dict and object access
            slide_dict = dict(slide) if hasattr(slide, 'keys') else slide
            image_path = slide_dict.get('image_path') if isinstance(slide_dict, dict) else getattr(slide, 'image_path', None)
            has_image = image_path and str(image_path) not in ('', 'None', 'none')
            slide_id = slide_dict.get('id') if isinstance(slide_dict, dict) else getattr(slide, 'id', None)
            slide_title = slide_dict.get('title', 'N/A') if isinstance(slide_dict, dict) else getattr(slide, 'title', 'N/A')
            
            print(f"  Slide {idx}: ID={slide_id}, Title={slide_title}, image_path={'SET' if has_image else 'MISSING'}, path={image_path}")
            
            # If image_path exists but is None or empty string, log warning
            if not has_image:
                print(f"    ⚠ WARNING: Slide {idx} (ID={slide_id}) has no valid image_path!")
            else:
                # Verify file exists
                import os
                static_path = os.path.join('static', str(image_path))
                file_exists = os.path.exists(static_path)
                print(f"    ✓ Image path: {image_path}, File exists: {file_exists}, Full path: {os.path.abspath(static_path) if file_exists else 'NOT FOUND'}")
        
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
        
        # Get public announcements (from public_announcements table OR posts with is_public flag)
        cursor.execute("""
            SELECT DISTINCT p.id, p.post_title, p.post_content, p.post_type, p.created_at, 
                   p.attachment_path, p.attachment_name, p.attachment_type,
                   COALESCE(pa.display_order, 0) as display_order
            FROM posts p
            LEFT JOIN public_announcements pa ON p.id = pa.post_id
            WHERE p.status = 'Active' 
              AND (p.is_public = 1 OR (pa.is_active = 1 AND pa.display_on_homepage = 1))
            ORDER BY display_order ASC, p.created_at DESC
            LIMIT 5
        """)
        announcements = cursor.fetchall()
        
        # Get public studies (featured/recent)
        cursor.execute("""
            SELECT s.id, s.study_title, s.summary, s.content_body, s.publish_date, s.author,
                   s.attachment_path, s.attachment_name, s.attachment_type,
                   sc.category_name
            FROM studies s
            LEFT JOIN study_categories sc ON s.category_id = sc.id
            WHERE s.status = 'Published' AND s.is_public = 1
            ORDER BY s.is_featured DESC, s.publish_date DESC, s.created_at DESC
            LIMIT 6
        """)
        public_studies = cursor.fetchall()
        
    except Exception as e:
        import traceback
        print(f"Error loading homepage data: {str(e)}")
        traceback.print_exc()
        hero_slides = []
        services = []
        gallery_photos = []
        about_intro = None
        announcements = []
        public_studies = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/homepage.html',
                         hero_slides=hero_slides,
                         services=services,
                         gallery_photos=gallery_photos,
                         about_intro=about_intro,
                         announcements=announcements,
                         public_studies=public_studies)

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

@public_website.route('/donation')
def donation_page():
    """Donation page with Chapa payment integration"""
    # Check if donation module is enabled
    if get_donation_setting('donation_module_enabled', '1') != '1':
        flash('Donation module is currently disabled', 'info')
        return redirect(url_for('public_website.homepage'))
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        # Get active hero slides for donation page
        cursor.execute("""
            SELECT * FROM public_hero_slides 
            WHERE is_active = 1 
            ORDER BY display_order ASC
        """)
        hero_slides = cursor.fetchall()
        
        # Get active donation types
        cursor.execute("""
            SELECT * FROM donation_types 
            WHERE is_active = 1 
            ORDER BY name ASC
        """)
        donation_types = cursor.fetchall()
        
        # Get donation methods (bank info, etc.)
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
        
        # Get settings
        min_amount = float(get_donation_setting('min_donation_amount', '10'))
        max_amount = float(get_donation_setting('max_donation_amount', '1000000'))
        allow_any_amount = get_donation_setting('allow_any_amount', '1') == '1'
        currency = get_donation_setting('default_currency', 'ETB')
        
    except Exception as e:
        hero_slides = []
        donation_types = []
        donation_methods = []
        donation_message = None
        min_amount = 10
        max_amount = 1000000
        allow_any_amount = True
        currency = 'ETB'
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/donation.html',
                         hero_slides=hero_slides,
                         donation_types=donation_types,
                         donation_methods=donation_methods,
                         donation_message=donation_message,
                         min_amount=min_amount,
                         max_amount=max_amount,
                         allow_any_amount=allow_any_amount,
                         currency=currency)

@public_website.route('/donation/process', methods=['POST'])
def process_donation():
    """Process donation and initiate Chapa payment"""
    try:
        # Get form data
        donation_type_id = request.form.get('donation_type_id', type=int)
        amount = float(request.form.get('amount', 0))
        donor_name = request.form.get('donor_name', '').strip()
        christian_name = request.form.get('christian_name', '').strip()
        donor_email = request.form.get('donor_email', '').strip()
        donor_phone = request.form.get('donor_phone', '').strip()
        is_anonymous = 1 if request.form.get('is_anonymous') else 0
        
        # Validate amount
        min_amount = float(get_donation_setting('min_donation_amount', '10'))
        max_amount = float(get_donation_setting('max_donation_amount', '1000000'))
        
        if amount < min_amount:
            flash(f'Minimum donation amount is {min_amount} ETB', 'error')
            return redirect(url_for('public_website.donation_page'))
        
        if amount > max_amount:
            flash(f'Maximum donation amount is {max_amount} ETB', 'error')
            return redirect(url_for('public_website.donation_page'))
        
        # Email is optional - only validate format if provided
        if donor_email and '@' not in donor_email:
            flash('Please provide a valid email address or leave it empty', 'error')
            return redirect(url_for('public_website.donation_page'))
        
        # Get Chapa settings
        chapa_secret_key = get_donation_setting('chapa_secret_key', '')
        chapa_public_key = get_donation_setting('chapa_public_key', '')
        currency = get_donation_setting('default_currency', 'ETB')
        callback_url = get_donation_setting('callback_url', '')
        redirect_url = get_donation_setting('redirect_url_after_payment', '/donation/thank-you')
        
        if not chapa_secret_key:
            flash('Payment gateway is not configured. Please contact administrator.', 'error')
            return redirect(url_for('public_website.donation_page'))
        
        # Create donation record
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate unique transaction reference
        tx_ref = f"MD_{uuid.uuid4().hex[:16].upper()}"
        
        # Insert donation record - Status is 'Completed' because transaction is automatically deducted
        cursor.execute("""
            INSERT INTO donations 
            (donation_type_id, donor_name, christian_name, donor_email, donor_phone, is_anonymous, 
             amount, currency, payment_status, payment_method, chapa_reference, tx_ref,
             ip_address, user_agent, paid_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Completed', 'Chapa', %s, %s, %s, %s, NOW())
        """, (donation_type_id, donor_name if not is_anonymous else 'Anonymous', 
              christian_name if not is_anonymous else '', donor_email or None, donor_phone or None, is_anonymous, 
              amount, currency, tx_ref, tx_ref,
              request.remote_addr, request.headers.get('User-Agent', '')))
        
        donation_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        # Prepare Chapa API request
        # Split name into first and last name
        name_parts = donor_name.split(' ', 1) if donor_name else ['Donor', '']
        first_name = name_parts[0] if name_parts else 'Donor'
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Build callback URL if not set
        if not callback_url:
            callback_url = request.url_root.rstrip('/') + '/donation/callback'
        
        # Chapa API endpoint
        chapa_url = "https://api.chapa.co/v1/transaction/initialize"
        
        # Prepare request data
        headers = {
            "Authorization": f"Bearer {chapa_secret_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "amount": str(amount),
            "currency": currency,
            "email": donor_email,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": donor_phone or "0900000000",
            "tx_ref": tx_ref,
            "callback_url": callback_url,
            "return_url": request.url_root.rstrip('/') + redirect_url + f"?donation_id={donation_id}&tx_ref={tx_ref}",
            "meta": {
                "donation_id": donation_id,
                "donation_type_id": donation_type_id or 0
            }
        }
        
        # Make request to Chapa
        response = requests.post(chapa_url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success' and result.get('data', {}).get('checkout_url'):
                # Update donation record with transaction ID if available
                checkout_url = result['data']['checkout_url']
                transaction_id = result.get('data', {}).get('id', '')
                
                if transaction_id:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE donations 
                        SET transaction_id = %s, chapa_response = %s
                        WHERE id = %s
                    """, (transaction_id, json.dumps(result), donation_id))
                    conn.commit()
                    cursor.close()
                    conn.close()
                
                # Redirect to Chapa checkout
                return redirect(checkout_url)
            else:
                flash('Payment initialization failed. Please try again.', 'error')
        else:
            flash(f'Payment gateway error: {response.text}', 'error')
        
    except Exception as e:
        flash(f'Error processing donation: {str(e)}', 'error')
        print(f"Donation processing error: {str(e)}")
    
    return redirect(url_for('public_website.donation_page'))

@public_website.route('/donation/callback', methods=['POST'])
def donation_callback():
    """Handle Chapa payment callback"""
    try:
        # Get callback data
        callback_data = request.get_json() or request.form.to_dict()
        tx_ref = callback_data.get('tx_ref', '')
        
        if not tx_ref:
            return jsonify({'status': 'error', 'message': 'Missing transaction reference'}), 400
        
        # Get donation record
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        cursor.execute("SELECT * FROM donations WHERE chapa_reference = %s OR tx_ref = %s", (tx_ref, tx_ref))
        donation = cursor.fetchone()
        
        if not donation:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Donation record not found'}), 404
        
        # Verify payment with Chapa
        chapa_secret_key = get_donation_setting('chapa_secret_key', '')
        if chapa_secret_key:
            verify_url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
            headers = {"Authorization": f"Bearer {chapa_secret_key}"}
            
            verify_response = requests.get(verify_url, headers=headers, timeout=30)
            
            if verify_response.status_code == 200:
                verify_result = verify_response.json()
                
                if verify_result.get('status') == 'success':
                    data = verify_result.get('data', {})
                    status = data.get('status', '')
                    
                    # Update donation record
                    if status == 'successful':
                        cursor.execute("""
                            UPDATE donations 
                            SET payment_status = 'Paid', 
                                transaction_id = %s,
                                chapa_response = %s,
                                paid_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (data.get('id', ''), json.dumps(verify_result), donation['id']))
                        conn.commit()
                    else:
                        cursor.execute("""
                            UPDATE donations 
                            SET payment_status = 'Failed',
                                chapa_response = %s
                            WHERE id = %s
                        """, (json.dumps(verify_result), donation['id']))
                        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Callback error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@public_website.route('/donation/thank-you')
def donation_thank_you():
    """Thank you page after donation"""
    donation_id = request.args.get('donation_id', type=int)
    tx_ref = request.args.get('tx_ref', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    donation = None
    if donation_id:
        try:
            cursor.execute("""
                SELECT d.*, dt.name as donation_type_name, dt.name_amharic as donation_type_name_amharic
                FROM donations d
                LEFT JOIN donation_types dt ON d.donation_type_id = dt.id
                WHERE d.id = %s
            """, (donation_id,))
            donation = cursor.fetchone()
        except:
            pass
    
    # Get thank you messages
    thank_you_message = get_donation_setting('thank_you_message', 'Thank you for your generous donation!')
    thank_you_message_amharic = get_donation_setting('thank_you_message_amharic', 'ለቸር ለግስናዎ እናመሰግናለን!')
    
    cursor.close()
    conn.close()
    
    return render_template('public/donation_thank_you.html',
                         donation=donation,
                         thank_you_message=thank_you_message,
                         thank_you_message_amharic=thank_you_message_amharic)

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
    """Public announcements page - shows all public posts/announcements"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        # Get all public announcements (from public_announcements table OR posts with is_public flag)
        cursor.execute("""
            SELECT DISTINCT p.id, p.post_title, p.post_content, p.post_type, 
                   p.created_at, p.start_date, p.end_date,
                   p.attachment_path, p.attachment_name, p.attachment_type,
                   COALESCE(pa.display_order, 0) as display_order,
                   p.views_count
            FROM posts p
            LEFT JOIN public_announcements pa ON p.id = pa.post_id
            WHERE p.status = 'Active' 
              AND (p.is_public = 1 OR (pa.is_active = 1))
            ORDER BY display_order ASC, p.created_at DESC
        """)
        announcements = cursor.fetchall()
    except Exception as e:
        announcements = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/announcements.html', announcements=announcements)

@public_website.route('/announcements/<int:post_id>')
def announcement_detail(post_id):
    """Public announcement detail page"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT DISTINCT p.*, pa.display_order
            FROM posts p
            LEFT JOIN public_announcements pa ON p.id = pa.post_id
            WHERE p.id = %s 
              AND p.status = 'Active' 
              AND (p.is_public = 1 OR (pa.is_active = 1))
        """, (post_id,))
        announcement = cursor.fetchone()
        
        if announcement:
            # Increment views count
            cursor.execute("UPDATE posts SET views_count = views_count + 1 WHERE id = %s", (post_id,))
            conn.commit()
        else:
            announcement = None
    except Exception as e:
        announcement = None
    finally:
        cursor.close()
        conn.close()
    
    if not announcement:
        return render_template('public/404.html'), 404
    
    return render_template('public/announcement_detail.html', announcement=announcement)

@public_website.route('/studies')
def studies_page():
    """Public studies page - shows all public study materials"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    category_filter = request.args.get('category', None)
    
    try:
        query = """
            SELECT s.id, s.study_title, s.summary, s.content_body, s.publish_date, s.author,
                   s.attachment_path, s.attachment_name, s.attachment_type,
                   s.views_count, s.downloads_count, s.is_featured,
                   sc.id as category_id, sc.category_name
            FROM studies s
            LEFT JOIN study_categories sc ON s.category_id = sc.id
            WHERE s.status = 'Published' AND s.is_public = 1
        """
        params = []
        
        if category_filter:
            query += " AND s.category_id = %s"
            params.append(category_filter)
        
        query += " ORDER BY s.is_featured DESC, s.publish_date DESC, s.created_at DESC"
        
        cursor.execute(query, params)
        studies = cursor.fetchall()
        
        # Get categories for filter
        cursor.execute("""
            SELECT DISTINCT sc.id, sc.category_name,
                   COUNT(s.id) as study_count
            FROM study_categories sc
            LEFT JOIN studies s ON sc.id = s.category_id AND s.is_public = 1 AND s.status = 'Published'
            GROUP BY sc.id, sc.category_name
            HAVING study_count > 0
            ORDER BY sc.category_name ASC
        """)
        categories = cursor.fetchall()
        
    except Exception as e:
        studies = []
        categories = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('public/studies.html', studies=studies, categories=categories, selected_category=category_filter)

@public_website.route('/studies/<int:study_id>')
def study_detail(study_id):
    """Public study detail page"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    try:
        cursor.execute("""
            SELECT s.*, sc.category_name
            FROM studies s
            LEFT JOIN study_categories sc ON s.category_id = sc.id
            WHERE s.id = %s AND s.status = 'Published' AND s.is_public = 1
        """, (study_id,))
        study = cursor.fetchone()
        
        if study:
            # Increment views count
            cursor.execute("UPDATE studies SET views_count = views_count + 1 WHERE id = %s", (study_id,))
            conn.commit()
        else:
            study = None
    except Exception as e:
        study = None
    finally:
        cursor.close()
        conn.close()
    
    if not study:
        return render_template('public/404.html'), 404
    
    return render_template('public/study_detail.html', study=study)

# Export blueprint
__all__ = ['public_website']

