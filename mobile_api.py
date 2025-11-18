"""
Mobile App API Endpoints
Provides RESTful API for Mikha Denagil Mobile Application
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import hashlib
import jwt
import datetime
from database import get_db_connection

# Create API blueprint
mobile_api = Blueprint('mobile_api', __name__, url_prefix='/api/v1')

# JWT Secret Key (should be in config)
JWT_SECRET = "your-secret-key-change-in-production"

def token_required(f):
    """Decorator to protect API endpoints"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user_id = data['user_id']
            current_member_id = data['member_id']
        except:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user_id, current_member_id, *args, **kwargs)
    
    return decorated

#  =====================
#  Authentication Endpoints
#  =====================

@mobile_api.route('/auth/login', methods=['POST'])
def mobile_login():
    """
    Member login endpoint
    POST /api/v1/auth/login
    Body: {"username": "string", "password": "string"}
    Returns: {"token": "jwt_token", "member": {...}}
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Get account
        cursor.execute("""
            SELECT ma.id, ma.member_id, ma.username, ma.account_status, ma.locked_until,
                   m.full_name, m.section_name, m.phone, m.email, m.gender
            FROM member_accounts ma
            JOIN member_registration m ON ma.member_id = m.id
            WHERE ma.username = %s AND ma.password_hash = %s
        """, (username, password_hash))
        
        account = cursor.fetchone()
        
        if not account:
            # Log failed attempt
            cursor.execute("""
                INSERT INTO member_login_history (member_account_id, status, failure_reason, ip_address, platform)
                VALUES ((SELECT id FROM member_accounts WHERE username = %s), 'Failed', 'Invalid credentials', %s, 'Mobile')
            """, (username, request.remote_addr))
            conn.commit()
            
            return jsonify({'error': 'Invalid username or password'}), 401
        
        account_id, member_id, username, status, locked_until, full_name, section_name, phone, email, gender = account
        
        # Check account status
        if status != 'Active':
            return jsonify({'error': f'Account is {status}'}), 403
        
        # Check if locked
        if locked_until and datetime.datetime.now() < locked_until:
            return jsonify({'error': 'Account is temporarily locked'}), 403
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': account_id,
            'member_id': member_id,
            'username': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)
        }, JWT_SECRET, algorithm="HS256")
        
        # Update last login
        cursor.execute("""
            UPDATE member_accounts SET last_login = NOW(), login_attempts = 0 WHERE id = %s
        """, (account_id,))
        
        # Log successful login
        cursor.execute("""
            INSERT INTO member_login_history (member_account_id, status, ip_address, platform, device_info)
            VALUES (%s, 'Success', %s, 'Mobile', %s)
        """, (account_id, request.remote_addr, request.headers.get('User-Agent')))
        
        conn.commit()
        
        return jsonify({
            'token': token,
            'member': {
                'id': member_id,
                'full_name': full_name,
                'section': section_name,
                'phone': phone,
                'email': email,
                'gender': gender,
                'username': username
            }
        }), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@mobile_api.route('/auth/change-password', methods=['POST'])
@token_required
def change_password(user_id, member_id):
    """
    Change password
    POST /api/v1/auth/change-password
    Headers: {"Authorization": "Bearer <token>"}
    Body: {"old_password": "string", "new_password": "string"}
    """
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': 'Old and new passwords required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        old_hash = hashlib.sha256(old_password.encode()).hexdigest()
        
        # Verify old password
        cursor.execute("""
            SELECT id FROM member_accounts WHERE id = %s AND password_hash = %s
        """, (user_id, old_hash))
        
        if not cursor.fetchone():
            return jsonify({'error': 'Old password incorrect'}), 400
        
        # Update password
        new_hash = hashlib.sha256(new_password.encode()).hexdigest()
        cursor.execute("""
            UPDATE member_accounts SET password_hash = %s WHERE id = %s
        """, (new_hash, user_id))
        conn.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

#  =====================
#  Member Profile Endpoints
#  =====================

@mobile_api.route('/member/profile', methods=['GET'])
@token_required
def get_profile(user_id, member_id):
    """
    Get member profile
    GET /api/v1/member/profile
    Headers: {"Authorization": "Bearer <token>"}
    """
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("""
            SELECT full_name, section_name, phone, email, gender, 
                   marital_status, date_of_birth, subcity, woreda, house_number
            FROM member_registration WHERE id = %s
        """, (member_id,))
        
        member = cursor.fetchone()
        
        if not member:
            return jsonify({'error': 'Member not found'}), 404
        
        return jsonify({
            'full_name': member[0],
            'section': member[1],
            'phone': member[2],
            'email': member[3],
            'gender': member[4],
            'marital_status': member[5],
            'date_of_birth': str(member[6]) if member[6] else None,
            'subcity': member[7],
            'woreda': member[8],
            'house_number': member[9]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@mobile_api.route('/member/positions', methods=['GET'])
@token_required
def get_member_positions(user_id, member_id):
    """
    Get member's current positions
    GET /api/v1/member/positions
    Headers: {"Authorization": "Bearer <token>"}
    """
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("""
            SELECT p.position_title, d.department_name, mp.start_date,
                   p.position_level, mp.appointment_type
            FROM member_positions mp
            JOIN positions p ON mp.position_id = p.id
            LEFT JOIN departments d ON mp.department_id = d.id
            WHERE mp.member_id = %s AND mp.is_current = 1
        """, (member_id,))
        
        positions = cursor.fetchall()
        
        return jsonify({
            'positions': [
                {
                    'title': pos[0],
                    'department': pos[1],
                    'start_date': str(pos[2]),
                    'level': pos[3],
                    'type': pos[4]
                }
                for pos in positions
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

#  =====================
#  Attendance Endpoints
#  =====================

@mobile_api.route('/attendance/my-records', methods=['GET'])
@token_required
def get_my_attendance(user_id, member_id):
    """
    Get member's attendance records
    GET /api/v1/attendance/my-records?limit=50
    Headers: {"Authorization": "Bearer <token>"}
    """
    limit = request.args.get('limit', 50, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM attendance
            WHERE full_name = (SELECT full_name FROM member_registration WHERE id = %s)
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at) DESC
            LIMIT %s
        """, (member_id, limit))
        
        records = cursor.fetchall()
        
        return jsonify({
            'attendance': [
                {
                    'date': str(rec[0]),
                    'count': rec[1]
                }
                for rec in records
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

#  =====================
#  Contribution Endpoints
#  =====================

@mobile_api.route('/contributions/my-history', methods=['GET'])
@token_required
def get_my_contributions(user_id, member_id):
    """
    Get member's contribution history
    GET /api/v1/contributions/my-history
    Headers: {"Authorization": "Bearer <token>"}
    """
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("""
            SELECT mc.contribution_date, mt.type_name, mc.amount, mc.payment_status
            FROM mewaco_contributions mc
            JOIN mewaco_types mt ON mc.contribution_type_id = mt.id
            WHERE mc.member_id = %s
            ORDER BY mc.contribution_date DESC
        """, (member_id,))
        
        contributions = cursor.fetchall()
        
        return jsonify({
            'contributions': [
                {
                    'date': str(cont[0]),
                    'type': cont[1],
                    'amount': float(cont[2]),
                    'status': cont[3]
                }
                for cont in contributions
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

#  =====================
#  Posts & Announcements Endpoints
#  =====================

@mobile_api.route('/posts', methods=['GET'])
@token_required
def get_posts(user_id, member_id):
    """
    Get posts relevant to member's section
    GET /api/v1/posts?limit=20&offset=0&type=Event
    Headers: {"Authorization": "Bearer <token>"}
    """
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    post_type = request.args.get('type', '', type=str)
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        # Get member's section and medebe
        cursor.execute("""
            SELECT m.section_name, mma.medebe_id
            FROM member_registration m
            LEFT JOIN member_medebe_assignment mma ON m.id = mma.member_id
            WHERE m.id = %s
        """, (member_id,))
        
        member_info = cursor.fetchone()
        if not member_info:
            return jsonify({'error': 'Member not found'}), 404
        
        member_section, member_medebe_id = member_info
        
        # Build query
        query = """
            SELECT 
                p.id, p.post_title, p.post_content, p.post_type, p.target_section,
                p.start_date, p.end_date, p.attachment_path, p.attachment_name,
                p.attachment_type, p.priority, p.created_at, p.created_by,
                p.views_count, m.medebe_name,
                (SELECT COUNT(*) FROM post_read_status WHERE post_id = p.id AND member_id = %s) as is_read
            FROM posts p
            LEFT JOIN medebe m ON p.target_medebe_id = m.id
            WHERE p.status = 'Active'
            AND (
                p.target_section = 'All Sections'
                OR p.target_section = %s
                OR (p.target_medebe_id = %s AND p.target_medebe_id IS NOT NULL)
            )
            AND (
                p.start_date IS NULL 
                OR p.start_date <= CURDATE()
            )
            AND (
                p.end_date IS NULL 
                OR p.end_date >= CURDATE()
            )
        """
        
        params = [member_id, member_section, member_medebe_id]
        
        if post_type:
            query += " AND p.post_type = %s"
            params.append(post_type)
        
        query += " ORDER BY p.priority DESC, p.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        posts = cursor.fetchall()
        
        return jsonify({
            'posts': [
                {
                    'id': post[0],
                    'title': post[1],
                    'content': post[2],
                    'type': post[3],
                    'target_section': post[4],
                    'start_date': str(post[5]) if post[5] else None,
                    'end_date': str(post[6]) if post[6] else None,
                    'attachment_url': f"/{post[7]}" if post[7] else None,
                    'attachment_name': post[8],
                    'attachment_type': post[9],
                    'priority': post[10],
                    'created_at': post[11].strftime('%Y-%m-%d %H:%M:%S') if post[11] else None,
                    'created_by': post[12],
                    'views_count': post[13],
                    'medebe_name': post[14],
                    'is_read': post[15] > 0
                }
                for post in posts
            ],
            'count': len(posts),
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@mobile_api.route('/posts/<int:post_id>', methods=['GET'])
@token_required
def get_post_details(user_id, member_id, post_id):
    """
    Get single post details
    GET /api/v1/posts/<post_id>
    Headers: {"Authorization": "Bearer <token>"}
    """
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("""
            SELECT 
                p.id, p.post_title, p.post_content, p.post_type, p.target_section,
                p.start_date, p.end_date, p.attachment_path, p.attachment_name,
                p.attachment_type, p.priority, p.created_at, p.created_by,
                p.views_count, m.medebe_name,
                (SELECT COUNT(*) FROM post_read_status WHERE post_id = p.id AND member_id = %s) as is_read
            FROM posts p
            LEFT JOIN medebe m ON p.target_medebe_id = m.id
            WHERE p.id = %s AND p.status = 'Active'
        """, (member_id, post_id))
        
        post = cursor.fetchone()
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Mark as read
        cursor.execute("""
            INSERT IGNORE INTO post_read_status (post_id, member_id)
            VALUES (%s, %s)
        """, (post_id, member_id))
        
        # Increment view count
        cursor.execute("""
            UPDATE posts SET views_count = views_count + 1 WHERE id = %s
        """, (post_id,))
        
        conn.commit()
        
        return jsonify({
            'post': {
                'id': post[0],
                'title': post[1],
                'content': post[2],
                'type': post[3],
                'target_section': post[4],
                'start_date': str(post[5]) if post[5] else None,
                'end_date': str(post[6]) if post[6] else None,
                'attachment_url': f"/{post[7]}" if post[7] else None,
                'attachment_name': post[8],
                'attachment_type': post[9],
                'priority': post[10],
                'created_at': post[11].strftime('%Y-%m-%d %H:%M:%S') if post[11] else None,
                'created_by': post[12],
                'views_count': post[13] + 1,
                'medebe_name': post[14],
                'is_read': True
            }
        }), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@mobile_api.route('/posts/<int:post_id>/mark-read', methods=['POST'])
@token_required
def mark_post_read_mobile(user_id, member_id, post_id):
    """
    Mark a post as read
    POST /api/v1/posts/<post_id>/mark-read
    Headers: {"Authorization": "Bearer <token>"}
    """
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("""
            INSERT IGNORE INTO post_read_status (post_id, member_id)
            VALUES (%s, %s)
        """, (post_id, member_id))
        
        cursor.execute("""
            UPDATE posts SET views_count = views_count + 1 WHERE id = %s
        """, (post_id,))
        
        conn.commit()
        
        return jsonify({'message': 'Post marked as read', 'success': True}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@mobile_api.route('/posts/stats', methods=['GET'])
@token_required
def get_posts_stats(user_id, member_id):
    """
    Get posts statistics for member
    GET /api/v1/posts/stats
    Headers: {"Authorization": "Bearer <token>"}
    """
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        # Get member's section
        cursor.execute("""
            SELECT section_name FROM member_registration WHERE id = %s
        """, (member_id,))
        member_section = cursor.fetchone()[0]
        
        # Get total posts for member
        cursor.execute("""
            SELECT COUNT(*) FROM posts
            WHERE status = 'Active'
            AND (target_section = 'All Sections' OR target_section = %s)
        """, (member_section,))
        total_posts = cursor.fetchone()[0]
        
        # Get read posts
        cursor.execute("""
            SELECT COUNT(*) FROM post_read_status WHERE member_id = %s
        """, (member_id,))
        read_posts = cursor.fetchone()[0]
        
        # Get unread posts
        unread_posts = total_posts - read_posts if total_posts > read_posts else 0
        
        return jsonify({
            'total_posts': total_posts,
            'read_posts': read_posts,
            'unread_posts': unread_posts
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

#  =====================
#  Study Materials Endpoints
#  =====================

@mobile_api.route('/studies', methods=['GET'])
@token_required
def get_studies(user_id, member_id):
    """
    Get study materials relevant to member's section
    GET /api/v1/studies?limit=20&offset=0&category_id=1
    Headers: {"Authorization": "Bearer <token>"}
    """
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    category_id = request.args.get('category_id', '', type=str)
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        # Get member's section
        cursor.execute("""
            SELECT section_name FROM member_registration WHERE id = %s
        """, (member_id,))
        
        member_info = cursor.fetchone()
        if not member_info:
            return jsonify({'error': 'Member not found'}), 404
        
        member_section = member_info[0]
        
        # Build query
        query = """
            SELECT 
                s.id, s.study_title, s.category_id, sc.category_name, s.target_audience,
                s.summary, s.attachment_path, s.attachment_name, s.attachment_type,
                s.publish_date, s.author, s.views_count, s.downloads_count,
                s.is_featured, s.tags, s.created_at,
                (SELECT COUNT(*) FROM study_read_status WHERE study_id = s.id AND member_id = %s) as is_read
            FROM studies s
            JOIN study_categories sc ON s.category_id = sc.id
            WHERE s.status = 'Published'
            AND (s.target_audience = 'All Members' OR s.target_audience = %s)
        """
        
        params = [member_id, member_section]
        
        if category_id:
            query += " AND s.category_id = %s"
            params.append(category_id)
        
        query += " ORDER BY s.is_featured DESC, s.publish_date DESC, s.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        studies = cursor.fetchall()
        
        return jsonify({
            'studies': [
                {
                    'id': study[0],
                    'title': study[1],
                    'category_id': study[2],
                    'category_name': study[3],
                    'target_audience': study[4],
                    'summary': study[5],
                    'attachment_url': f"/{study[6]}" if study[6] else None,
                    'attachment_name': study[7],
                    'attachment_type': study[8],
                    'publish_date': str(study[9]) if study[9] else None,
                    'author': study[10],
                    'views_count': study[11],
                    'downloads_count': study[12],
                    'is_featured': study[13] == 1,
                    'tags': study[14],
                    'created_at': study[15].strftime('%Y-%m-%d %H:%M:%S') if study[15] else None,
                    'is_read': study[16] > 0
                }
                for study in studies
            ],
            'count': len(studies),
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@mobile_api.route('/studies/<int:study_id>', methods=['GET'])
@token_required
def get_study_details(user_id, member_id, study_id):
    """
    Get single study details with full content
    GET /api/v1/studies/<study_id>
    Headers: {"Authorization": "Bearer <token>"}
    """
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("""
            SELECT 
                s.id, s.study_title, s.category_id, sc.category_name, s.target_audience,
                s.content_body, s.summary, s.attachment_path, s.attachment_name, s.attachment_type,
                s.publish_date, s.author, s.views_count, s.downloads_count,
                s.is_featured, s.tags, s.created_at,
                (SELECT COUNT(*) FROM study_read_status WHERE study_id = s.id AND member_id = %s) as is_read
            FROM studies s
            JOIN study_categories sc ON s.category_id = sc.id
            WHERE s.id = %s AND s.status = 'Published'
        """, (member_id, study_id))
        
        study = cursor.fetchone()
        
        if not study:
            return jsonify({'error': 'Study not found'}), 404
        
        # Mark as read
        cursor.execute("""
            INSERT IGNORE INTO study_read_status (study_id, member_id)
            VALUES (%s, %s)
        """, (study_id, member_id))
        
        # Increment view count
        cursor.execute("""
            UPDATE studies SET views_count = views_count + 1 WHERE id = %s
        """, (study_id,))
        
        conn.commit()
        
        return jsonify({
            'study': {
                'id': study[0],
                'title': study[1],
                'category_id': study[2],
                'category_name': study[3],
                'target_audience': study[4],
                'content_body': study[5],
                'summary': study[6],
                'attachment_url': f"/{study[7]}" if study[7] else None,
                'attachment_name': study[8],
                'attachment_type': study[9],
                'publish_date': str(study[10]) if study[10] else None,
                'author': study[11],
                'views_count': study[12] + 1,
                'downloads_count': study[13],
                'is_featured': study[14] == 1,
                'tags': study[15],
                'created_at': study[16].strftime('%Y-%m-%d %H:%M:%S') if study[16] else None,
                'is_read': True
            }
        }), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@mobile_api.route('/study-categories', methods=['GET'])
@token_required
def get_study_categories(user_id, member_id):
    """
    Get all active study categories
    GET /api/v1/study-categories
    Headers: {"Authorization": "Bearer <token>"}
    """
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("""
            SELECT id, category_name, description, display_order
            FROM study_categories
            WHERE status = 'Active'
            ORDER BY display_order, category_name
        """)
        
        categories = cursor.fetchall()
        
        return jsonify({
            'categories': [
                {
                    'id': cat[0],
                    'name': cat[1],
                    'description': cat[2],
                    'display_order': cat[3]
                }
                for cat in categories
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@mobile_api.route('/studies/<int:study_id>/download', methods=['GET'])
@token_required
def download_study_attachment_mobile(user_id, member_id, study_id):
    """
    Download study attachment
    GET /api/v1/studies/<study_id>/download
    Headers: {"Authorization": "Bearer <token>"}
    """
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("""
            SELECT attachment_path, attachment_name 
            FROM studies 
            WHERE id = %s AND status = 'Published'
        """, (study_id,))
        
        result = cursor.fetchone()
        
        if result and result[0]:
            # Increment download count
            cursor.execute("""
                UPDATE studies SET downloads_count = downloads_count + 1 WHERE id = %s
            """, (study_id,))
            conn.commit()
            
            return jsonify({
                'download_url': f"/{result[0]}",
                'filename': result[1]
            }), 200
        else:
            return jsonify({'error': 'Attachment not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

#  =====================
#  Donation Endpoints (Flutter Mobile App)
#  =====================

@mobile_api.route('/donations/types', methods=['GET'])
def get_donation_types():
    """Get all active donation types"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        cursor.execute("""
            SELECT id, name, name_amharic, description, description_amharic, status
            FROM donation_types 
            WHERE status = 'active' OR is_active = 1
            ORDER BY name ASC
        """)
        types = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': types
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_api.route('/donations/initiate', methods=['POST'])
@token_required
def initiate_donation(current_user_id, current_member_id):
    """Initiate a donation payment via Chapa"""
    try:
        data = request.get_json()
        
        # Validate required fields (email is optional for mobile)
        required_fields = ['donation_type_id', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        donation_type_id = data.get('donation_type_id')
        amount = float(data.get('amount', 0))
        donor_name = data.get('donor_name', '')
        christian_name = data.get('christian_name', '')
        donor_email = data.get('donor_email', '')  # Optional for mobile
        donor_phone = data.get('donor_phone', '')
        is_anonymous = data.get('is_anonymous', False)
        
        # Validate amount first
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        # Get member info if available
        cursor.execute("SELECT full_name, email, phone FROM member_registration WHERE id = %s", (current_member_id,))
        member = cursor.fetchone()
        
        # Use member info as defaults if not provided
        if not donor_name and member:
            donor_name = member.get('full_name', '')
        if not donor_email and member:
            donor_email = member.get('email', '')
        if not donor_phone and member:
            donor_phone = member.get('phone', '')
        
        # Email is optional, but if provided, validate format
        if donor_email and '@' not in donor_email:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400
        
        # Get settings
        cursor.execute("SELECT setting_key, setting_value FROM donation_settings WHERE setting_key IN ('min_donation_amount', 'max_donation_amount', 'chapa_secret_key', 'default_currency')")
        settings = {row['setting_key']: row['setting_value'] for row in cursor.fetchall()}
        
        min_amount = float(settings.get('min_donation_amount', 10))
        max_amount = float(settings.get('max_donation_amount', 1000000))
        currency = settings.get('default_currency', 'ETB')
        chapa_secret_key = settings.get('chapa_secret_key', '')
        
        if amount < min_amount or amount > max_amount:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Amount must be between {min_amount} and {max_amount} {currency}'
            }), 400
        
        if not chapa_secret_key:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Payment gateway not configured'
            }), 500
        
        # Generate transaction reference
        import uuid
        tx_ref = f"MD_{uuid.uuid4().hex[:16].upper()}"
        
        # Create donation record
        cursor.execute("""
            INSERT INTO donations 
            (donation_type_id, donor_name, christian_name, donor_email, donor_phone, is_anonymous, 
             amount, currency, payment_status, payment_method, tx_ref, chapa_reference,
             ip_address, user_agent, paid_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Completed', 'Chapa', %s, %s, %s, %s, NOW())
        """, (donation_type_id, donor_name if not is_anonymous else 'Anonymous', 
              christian_name if not is_anonymous else '', donor_email, donor_phone, 1 if is_anonymous else 0, 
              amount, currency, tx_ref, tx_ref,
              request.remote_addr, request.headers.get('User-Agent', '')))
        
        donation_id = cursor.lastrowid
        
        # Prepare Chapa request
        import requests
        import json
        
        name_parts = donor_name.split(' ', 1) if donor_name else ['Donor', '']
        first_name = name_parts[0] if name_parts else 'Donor'
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        chapa_url = "https://api.chapa.co/v1/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {chapa_secret_key}",
            "Content-Type": "application/json"
        }
        
        callback_url = request.url_root.rstrip('/') + '/donation/callback'
        return_url = request.url_root.rstrip('/') + '/donation/thank-you'
        
        # Chapa requires email, use a default if not provided
        chapa_email = donor_email if donor_email else f"donor_{donation_id}@mikhadenagil.org"
        
        chapa_data = {
            "amount": str(amount),
            "currency": currency,
            "email": chapa_email,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": donor_phone or "0900000000",
            "tx_ref": tx_ref,
            "callback_url": callback_url,
            "return_url": return_url,
            "meta": {
                "donation_id": donation_id,
                "donation_type_id": donation_type_id or 0,
                "member_id": current_member_id,
                "source": "mobile_app"
            }
        }
        
        # Make request to Chapa
        response = requests.post(chapa_url, json=chapa_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success' and result.get('data', {}).get('checkout_url'):
                checkout_url = result['data']['checkout_url']
                transaction_id = result.get('data', {}).get('id', '')
                
                # Update donation record
                if transaction_id:
                    cursor.execute("""
                        UPDATE donations 
                        SET transaction_id = %s, chapa_response = %s
                        WHERE id = %s
                    """, (transaction_id, json.dumps(result), donation_id))
                    conn.commit()
                
                cursor.close()
                conn.close()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'donation_id': donation_id,
                        'checkout_url': checkout_url,
                        'tx_ref': tx_ref,
                        'amount': amount,
                        'currency': currency
                    }
                }), 200
            else:
                cursor.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Payment initialization failed'
                }), 500
        else:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Chapa API error: {response.text}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_api.route('/donations/verify/<tx_ref>', methods=['GET'])
@token_required
def verify_donation_payment(current_user_id, current_member_id, tx_ref):
    """Verify donation payment status from Chapa"""
    try:
        import requests
        import json
        import os
        from config import Config
        
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        # Get donation record
        cursor.execute("""
            SELECT d.*, dt.name as donation_type_name, dt.name_amharic as donation_type_name_amharic
            FROM donations d
            LEFT JOIN donation_types dt ON d.donation_type_id = dt.id
            WHERE d.tx_ref = %s OR d.chapa_reference = %s
        """, (tx_ref, tx_ref))
        
        donation = cursor.fetchone()
        
        if not donation:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Donation not found'
            }), 404
        
        # Get Chapa secret key
        cursor.execute("SELECT setting_value FROM donation_settings WHERE setting_key = 'chapa_secret_key'")
        setting = cursor.fetchone()
        chapa_secret_key = setting['setting_value'] if setting else os.environ.get('CHAPA_SECRET_KEY') or Config.CHAPA_SECRET_KEY
        
        if not chapa_secret_key:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Payment gateway not configured'
            }), 500
        
        # Verify with Chapa API
        chapa_url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
        headers = {
            "Authorization": f"Bearer {chapa_secret_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(chapa_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            # Update donation status based on Chapa response
            if result.get('status') == 'success':
                chapa_status = result.get('data', {}).get('status', '')
                
                # Map Chapa status to our status (treat pending as completed since auto-deducted)
                if chapa_status == 'successful':
                    payment_status = 'Completed'
                elif chapa_status == 'pending':
                    payment_status = 'Completed'  # Treat pending as completed since auto-deducted
                else:
                    payment_status = 'Failed'
                
                cursor.execute("""
                    UPDATE donations 
                    SET payment_status = %s,
                        transaction_id = %s,
                        chapa_response = %s,
                        paid_at = CASE WHEN %s = 'Completed' THEN NOW() ELSE paid_at END,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    payment_status,
                    result.get('data', {}).get('id', ''),
                    json.dumps(result),
                    payment_status,
                    donation['id']
                ))
                conn.commit()
                
                # Refresh donation data
                cursor.execute("""
                    SELECT d.*, dt.name as donation_type_name, dt.name_amharic as donation_type_name_amharic
                    FROM donations d
                    LEFT JOIN donation_types dt ON d.donation_type_id = dt.id
                    WHERE d.id = %s
                """, (donation['id'],))
                updated_donation = cursor.fetchone()
                
                # Convert datetime to ISO format
                if updated_donation.get('created_at'):
                    updated_donation['created_at'] = updated_donation['created_at'].isoformat() if hasattr(updated_donation['created_at'], 'isoformat') else str(updated_donation['created_at'])
                if updated_donation.get('paid_at'):
                    updated_donation['paid_at'] = updated_donation['paid_at'].isoformat() if hasattr(updated_donation['paid_at'], 'isoformat') else str(updated_donation['paid_at'])
                
                cursor.close()
                conn.close()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'donation': updated_donation,
                        'chapa_status': chapa_status,
                        'payment_status': payment_status
                    }
                }), 200
            else:
                cursor.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Payment verification failed',
                    'chapa_response': result
                }), 400
        else:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Chapa API error: {response.text}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_api.route('/donations/my-history', methods=['GET'])
@token_required
def get_my_donation_history(current_user_id, current_member_id):
    """Get donation history for logged-in member"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        # Get member email to match donations
        cursor.execute("SELECT email FROM aawsa_user WHERE payroll_number = %s", (current_user_id,))
        user = cursor.fetchone()
        
        if not user or not user.get('email'):
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'data': []
            }), 200
        
        # Get donations for this member (by email or member_id from meta)
        cursor.execute("""
            SELECT d.id, d.amount, d.currency, d.payment_status, d.payment_method,
                   d.tx_ref, d.chapa_reference, d.created_at, d.paid_at,
                   d.donor_name, d.christian_name,
                   dt.name as donation_type_name, dt.name_amharic as donation_type_name_amharic
            FROM donations d
            LEFT JOIN donation_types dt ON d.donation_type_id = dt.id
            WHERE (d.donor_email = %s OR JSON_EXTRACT(d.chapa_response, '$.meta.member_id') = %s)
            ORDER BY d.created_at DESC
            LIMIT 100
        """, (user['email'] if user else '', current_member_id))
        
        donations = cursor.fetchall()
        
        # Convert datetime to ISO format
        for donation in donations:
            if donation.get('created_at'):
                donation['created_at'] = donation['created_at'].isoformat() if hasattr(donation['created_at'], 'isoformat') else str(donation['created_at'])
            if donation.get('paid_at'):
                donation['paid_at'] = donation['paid_at'].isoformat() if hasattr(donation['paid_at'], 'isoformat') else str(donation['paid_at'])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': donations
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_api.route('/donations/<int:donation_id>', methods=['GET'])
@token_required
def get_donation_details(current_user_id, current_member_id, donation_id):
    """Get specific donation details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        cursor.execute("""
            SELECT d.*, dt.name as donation_type_name, dt.name_amharic as donation_type_name_amharic
            FROM donations d
            LEFT JOIN donation_types dt ON d.donation_type_id = dt.id
            WHERE d.id = %s
        """, (donation_id,))
        
        donation = cursor.fetchone()
        
        if not donation:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Donation not found'
            }), 404
        
        # Convert datetime to ISO format
        if donation.get('created_at'):
            donation['created_at'] = donation['created_at'].isoformat() if hasattr(donation['created_at'], 'isoformat') else str(donation['created_at'])
        if donation.get('paid_at'):
            donation['paid_at'] = donation['paid_at'].isoformat() if hasattr(donation['paid_at'], 'isoformat') else str(donation['paid_at'])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': donation
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

#  =====================
#  Utility Endpoints
#  =====================

@mobile_api.route('/health', methods=['GET'])
def health_check():
    """API health check"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.datetime.now().isoformat()
    }), 200

@mobile_api.route('/version', methods=['GET'])
def version():
    """Get API version"""
    return jsonify({
        'api_version': '1.1.0',
        'min_app_version': '1.0.0',
        'features': [
            'authentication',
            'profile',
            'positions',
            'attendance',
            'contributions',
            'posts',
            'announcements',
            'events',
            'donations'
        ]
    }), 200

#  =====================
#  MEWACO Payment Endpoints
#  =====================

@mobile_api.route('/mewaco/types', methods=['GET'])
@token_required
def get_mewaco_types(current_user_id, current_member_id):
    """Get all active MEWACO contribution types"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        cursor.execute("""
            SELECT id, type_name, description, default_amount, status
            FROM mewaco_types 
            WHERE status = 'Active'
            ORDER BY type_name ASC
        """)
        types = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': types
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_api.route('/mewaco/initiate', methods=['POST'])
@token_required
def initiate_mewaco_payment(current_user_id, current_member_id):
    """Initiate a MEWACO contribution payment via Chapa"""
    try:
        import requests
        import json
        import uuid
        import os
        from config import Config
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['mewaco_type_id', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        mewaco_type_id = data.get('mewaco_type_id')
        amount = float(data.get('amount', 0))
        contribution_date = data.get('contribution_date')  # Optional, defaults to today
        notes = data.get('notes', '')
        
        # Validate amount
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        # Get member info
        cursor.execute("SELECT full_name, email, phone FROM member_registration WHERE id = %s", (current_member_id,))
        member = cursor.fetchone()
        
        if not member:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Member not found'
            }), 404
        
        # Get MEWACO type info
        cursor.execute("SELECT type_name, default_amount FROM mewaco_types WHERE id = %s AND status = 'Active'", (mewaco_type_id,))
        mewaco_type = cursor.fetchone()
        
        if not mewaco_type:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'MEWACO type not found or inactive'
            }), 404
        
        # Get Chapa settings
        cursor.execute("SELECT setting_key, setting_value FROM donation_settings WHERE setting_key IN ('min_donation_amount', 'max_donation_amount', 'chapa_secret_key', 'default_currency')")
        settings = {row['setting_key']: row['setting_value'] for row in cursor.fetchall()}
        
        min_amount = float(settings.get('min_donation_amount', 10))
        max_amount = float(settings.get('max_donation_amount', 1000000))
        currency = settings.get('default_currency', 'ETB')
        chapa_secret_key = settings.get('chapa_secret_key') or os.environ.get('CHAPA_SECRET_KEY') or Config.CHAPA_SECRET_KEY
        
        if amount < min_amount or amount > max_amount:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Amount must be between {min_amount} and {max_amount} {currency}'
            }), 400
        
        if not chapa_secret_key:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Payment gateway not configured'
            }), 500
        
        # Generate transaction reference
        tx_ref = f"MEWACO_{uuid.uuid4().hex[:16].upper()}"
        
        # Use today's date if not provided
        from datetime import date
        if not contribution_date:
            contribution_date = date.today()
        else:
            contribution_date = date.fromisoformat(contribution_date) if isinstance(contribution_date, str) else contribution_date
        
        # Create MEWACO contribution record
        cursor.execute("""
            INSERT INTO mewaco_contributions 
            (member_id, mewaco_type_id, contribution_date, amount, payment_method, 
             payment_status, tx_ref, chapa_reference, ip_address, user_agent, paid_at)
            VALUES (%s, %s, %s, %s, 'Chapa', 'Completed', %s, %s, %s, %s, NOW())
        """, (
            current_member_id, 
            mewaco_type_id, 
            contribution_date, 
            amount, 
            tx_ref, 
            tx_ref,
            request.remote_addr, 
            request.headers.get('User-Agent', '')
        ))
        
        contribution_id = cursor.lastrowid
        
        # Prepare Chapa request
        name_parts = member['full_name'].split(' ', 1) if member.get('full_name') else ['Member', '']
        first_name = name_parts[0] if name_parts else 'Member'
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        chapa_url = "https://api.chapa.co/v1/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {chapa_secret_key}",
            "Content-Type": "application/json"
        }
        
        callback_url = request.url_root.rstrip('/') + '/mewaco/callback'
        return_url = request.url_root.rstrip('/') + '/mewaco/thank-you'
        
        # Chapa requires email, use member email or default
        chapa_email = member.get('email') or f"member_{current_member_id}@mikhadenagil.org"
        
        chapa_data = {
            "amount": str(amount),
            "currency": currency,
            "email": chapa_email,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": member.get('phone') or "0900000000",
            "tx_ref": tx_ref,
            "callback_url": callback_url,
            "return_url": return_url,
            "meta": {
                "contribution_id": contribution_id,
                "mewaco_type_id": mewaco_type_id,
                "member_id": current_member_id,
                "source": "mobile_app",
                "type": "mewaco"
            }
        }
        
        # Make request to Chapa
        response = requests.post(chapa_url, json=chapa_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success' and result.get('data', {}).get('checkout_url'):
                checkout_url = result['data']['checkout_url']
                transaction_id = result.get('data', {}).get('id', '')
                
                # Update contribution record
                if transaction_id:
                    cursor.execute("""
                        UPDATE mewaco_contributions 
                        SET transaction_id = %s, chapa_response = %s
                        WHERE id = %s
                    """, (transaction_id, json.dumps(result), contribution_id))
                    conn.commit()
                
                cursor.close()
                conn.close()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'contribution_id': contribution_id,
                        'checkout_url': checkout_url,
                        'tx_ref': tx_ref,
                        'amount': amount,
                        'currency': currency,
                        'mewaco_type': mewaco_type['type_name']
                    }
                }), 200
            else:
                cursor.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Payment initialization failed'
                }), 500
        else:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Chapa API error: {response.text}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_api.route('/mewaco/verify/<tx_ref>', methods=['GET'])
@token_required
def verify_mewaco_payment(current_user_id, current_member_id, tx_ref):
    """Verify MEWACO payment status from Chapa"""
    try:
        import requests
        import json
        import os
        from config import Config
        
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        # Get contribution record
        cursor.execute("""
            SELECT mc.*, mt.type_name
            FROM mewaco_contributions mc
            LEFT JOIN mewaco_types mt ON mc.mewaco_type_id = mt.id
            WHERE mc.tx_ref = %s OR mc.chapa_reference = %s
        """, (tx_ref, tx_ref))
        
        contribution = cursor.fetchone()
        
        if not contribution:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Contribution not found'
            }), 404
        
        # Get Chapa secret key
        cursor.execute("SELECT setting_value FROM donation_settings WHERE setting_key = 'chapa_secret_key'")
        setting = cursor.fetchone()
        chapa_secret_key = setting['setting_value'] if setting else os.environ.get('CHAPA_SECRET_KEY') or Config.CHAPA_SECRET_KEY
        
        if not chapa_secret_key:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Payment gateway not configured'
            }), 500
        
        # Verify with Chapa API
        chapa_url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
        headers = {
            "Authorization": f"Bearer {chapa_secret_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(chapa_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            # Update contribution status based on Chapa response
            if result.get('status') == 'success':
                chapa_status = result.get('data', {}).get('status', '')
                
                # Map Chapa status to our status
                if chapa_status == 'successful':
                    payment_status = 'Completed'
                elif chapa_status == 'pending':
                    payment_status = 'Completed'  # Treat pending as completed since auto-deducted
                else:
                    payment_status = 'Failed'
                
                cursor.execute("""
                    UPDATE mewaco_contributions 
                    SET payment_status = %s,
                        transaction_id = %s,
                        chapa_response = %s,
                        paid_at = CASE WHEN %s = 'Completed' THEN NOW() ELSE paid_at END,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    payment_status,
                    result.get('data', {}).get('id', ''),
                    json.dumps(result),
                    payment_status,
                    contribution['id']
                ))
                conn.commit()
                
                # Refresh contribution data
                cursor.execute("""
                    SELECT mc.*, mt.type_name
                    FROM mewaco_contributions mc
                    LEFT JOIN mewaco_types mt ON mc.mewaco_type_id = mt.id
                    WHERE mc.id = %s
                """, (contribution['id'],))
                updated_contribution = cursor.fetchone()
                
                # Convert datetime to ISO format
                if updated_contribution.get('contribution_date'):
                    updated_contribution['contribution_date'] = updated_contribution['contribution_date'].isoformat() if hasattr(updated_contribution['contribution_date'], 'isoformat') else str(updated_contribution['contribution_date'])
                if updated_contribution.get('paid_at'):
                    updated_contribution['paid_at'] = updated_contribution['paid_at'].isoformat() if hasattr(updated_contribution['paid_at'], 'isoformat') else str(updated_contribution['paid_at'])
                
                cursor.close()
                conn.close()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'contribution': updated_contribution,
                        'chapa_status': chapa_status,
                        'payment_status': payment_status
                    }
                }), 200
            else:
                cursor.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Payment verification failed',
                    'chapa_response': result
                }), 400
        else:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Chapa API error: {response.text}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_api.route('/mewaco/my-contributions', methods=['GET'])
@token_required
def get_my_mewaco_contributions(current_user_id, current_member_id):
    """Get MEWACO contribution history for logged-in member"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        cursor.execute("""
            SELECT mc.id, mc.contribution_date, mc.amount, mc.payment_status, mc.payment_method,
                   mc.tx_ref, mc.chapa_reference, mc.created_at, mc.paid_at,
                   mt.type_name, mt.description
            FROM mewaco_contributions mc
            LEFT JOIN mewaco_types mt ON mc.mewaco_type_id = mt.id
            WHERE mc.member_id = %s
            ORDER BY mc.contribution_date DESC, mc.created_at DESC
            LIMIT 100
        """, (current_member_id,))
        
        contributions = cursor.fetchall()
        
        # Convert datetime to ISO format
        for contribution in contributions:
            if contribution.get('contribution_date'):
                contribution['contribution_date'] = contribution['contribution_date'].isoformat() if hasattr(contribution['contribution_date'], 'isoformat') else str(contribution['contribution_date'])
            if contribution.get('created_at'):
                contribution['created_at'] = contribution['created_at'].isoformat() if hasattr(contribution['created_at'], 'isoformat') else str(contribution['created_at'])
            if contribution.get('paid_at'):
                contribution['paid_at'] = contribution['paid_at'].isoformat() if hasattr(contribution['paid_at'], 'isoformat') else str(contribution['paid_at'])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': contributions
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Export blueprint
__all__ = ['mobile_api']



