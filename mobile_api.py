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
            'events'
        ]
    }), 200

# Export blueprint
__all__ = ['mobile_api']



