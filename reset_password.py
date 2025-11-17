"""
Script to reset password for user/member ID 83659
"""
import hashlib
from database import get_db_connection
from auth import hash_password

def reset_password():
    """Reset password for ID 83659 to 12345678"""
    new_password = "12345678"
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        # Try to find in aawsa_user table by user_id
        cursor.execute("""
            SELECT user_id, payroll_number, username 
            FROM aawsa_user 
            WHERE user_id = %s
        """, (83659,))
        
        user = cursor.fetchone()
        
        if user:
            # Reset password for aawsa_user (uses Werkzeug hash)
            password_hash = hash_password(new_password)
            cursor.execute("""
                UPDATE aawsa_user 
                SET password_hash = %s 
                WHERE user_id = %s
            """, (password_hash, 83659))
            conn.commit()
            print(f"SUCCESS: Reset password for aawsa_user (user_id: 83659, payroll_number: {user[1]}, username: {user[2]})")
            cursor.close()
            conn.close()
            return
        
        # Try to find in aawsa_user table by payroll_number
        cursor.execute("""
            SELECT user_id, payroll_number, username 
            FROM aawsa_user 
            WHERE payroll_number = %s
        """, ('83659',))
        
        user = cursor.fetchone()
        
        if user:
            # Reset password for aawsa_user (uses Werkzeug hash)
            password_hash = hash_password(new_password)
            cursor.execute("""
                UPDATE aawsa_user 
                SET password_hash = %s 
                WHERE payroll_number = %s
            """, (password_hash, '83659'))
            conn.commit()
            print(f"SUCCESS: Reset password for aawsa_user (payroll_number: 83659, username: {user[2]})")
            cursor.close()
            conn.close()
            return
        
        # Try to find in member_accounts table by member_id
        cursor.execute("""
            SELECT id, member_id, username 
            FROM member_accounts 
            WHERE member_id = %s
        """, (83659,))
        
        account = cursor.fetchone()
        
        if account:
            # Reset password for member_accounts (uses SHA256 hash)
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            cursor.execute("""
                UPDATE member_accounts 
                SET password_hash = %s, login_attempts = 0, locked_until = NULL
                WHERE member_id = %s
            """, (password_hash, 83659))
            conn.commit()
            print(f"SUCCESS: Reset password for member_accounts (member_id: 83659, username: {account[2]})")
            cursor.close()
            conn.close()
            return
        
        # Try to find in member_accounts table by account id
        cursor.execute("""
            SELECT id, member_id, username 
            FROM member_accounts 
            WHERE id = %s
        """, (83659,))
        
        account = cursor.fetchone()
        
        if account:
            # Reset password for member_accounts (uses SHA256 hash)
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            cursor.execute("""
                UPDATE member_accounts 
                SET password_hash = %s, login_attempts = 0, locked_until = NULL
                WHERE id = %s
            """, (password_hash, 83659))
            conn.commit()
            print(f"SUCCESS: Reset password for member_accounts (account id: 83659, username: {account[2]})")
            cursor.close()
            conn.close()
            return
        
        # Try to find in member_accounts by username
        cursor.execute("""
            SELECT id, member_id, username 
            FROM member_accounts 
            WHERE username = %s
        """, ('83659',))
        
        account = cursor.fetchone()
        
        if account:
            # Reset password for member_accounts (uses SHA256 hash)
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            cursor.execute("""
                UPDATE member_accounts 
                SET password_hash = %s, login_attempts = 0, locked_until = NULL
                WHERE username = %s
            """, (password_hash, '83659'))
            conn.commit()
            print(f"SUCCESS: Reset password for member_accounts (username: 83659, member_id: {account[1]})")
            cursor.close()
            conn.close()
            return
        
        # Try to find member by phone number containing 83659
        cursor.execute("""
            SELECT id, full_name, phone 
            FROM member_registration 
            WHERE phone LIKE %s
        """, ('%83659%',))
        
        member = cursor.fetchone()
        
        if member:
            # Check if account exists for this member
            cursor.execute("""
                SELECT id, member_id, username 
                FROM member_accounts 
                WHERE member_id = %s
            """, (member[0],))
            
            account = cursor.fetchone()
            
            if account:
                # Reset password for existing account
                password_hash = hashlib.sha256(new_password.encode()).hexdigest()
                cursor.execute("""
                    UPDATE member_accounts 
                    SET password_hash = %s, login_attempts = 0, locked_until = NULL
                    WHERE member_id = %s
                """, (password_hash, member[0]))
                conn.commit()
                print(f"SUCCESS: Reset password for member_accounts (member_id: {member[0]}, name: {member[1]}, phone: {member[2]})")
            else:
                print(f"INFO: Found member (id: {member[0]}, name: {member[1]}, phone: {member[2]}) but no account exists")
                print("  Cannot reset password - account must be created first")
            cursor.close()
            conn.close()
            return
        
        # Check if member with ID 83659 exists but has no account
        cursor.execute("""
            SELECT id, full_name, phone, email 
            FROM member_registration 
            WHERE id = %s
        """, (83659,))
        
        member = cursor.fetchone()
        
        if member:
            # Create account for this member with the specified password
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            
            # Generate username from member name
            username = str(member[0])  # Use member ID as username
            
            # Check if username already exists
            cursor.execute("SELECT COUNT(*) FROM member_accounts WHERE username = %s", (username,))
            if cursor.fetchone()[0] > 0:
                username = f"member{member[0]}"
            
            cursor.execute("""
                INSERT INTO member_accounts (member_id, username, password_hash, email, phone, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (member[0], username, password_hash, member[3] if len(member) > 3 else None, member[2], 'SYSTEM'))
            conn.commit()
            print(f"SUCCESS: Created account and set password for member (id: {member[0]}, name: {member[1]}, username: {username})")
            cursor.close()
            conn.close()
            return
        
        print("ERROR: No user or member account found with ID 83659")
        print("  Searched in:")
        print("    - aawsa_user table (user_id = 83659)")
        print("    - aawsa_user table (payroll_number = '83659')")
        print("    - member_accounts table (member_id = 83659)")
        print("    - member_accounts table (id = 83659)")
        print("    - member_accounts table (username = '83659')")
        print("    - member_registration table (phone contains '83659')")
        print("    - member_registration table (id = 83659)")
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR: Error resetting password: {str(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    reset_password()

