"""
Script to reset password for ID 83659 to 12345678
Checks both aawsa_user and member_accounts tables
"""
import hashlib
from database import get_db_connection
from auth import hash_password

def reset_password():
    """Reset password for ID 83659"""
    account_id = 83659
    new_password = "12345678"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if it's a member_accounts ID
        cursor.execute("SELECT id, username, member_id FROM member_accounts WHERE id = %s", (account_id,))
        member_account = cursor.fetchone()
        
        if member_account:
            # Reset password for member_accounts (uses SHA256)
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            cursor.execute("""
                UPDATE member_accounts 
                SET password_hash = %s, login_attempts = 0, locked_until = NULL
                WHERE id = %s
            """, (password_hash, account_id))
            conn.commit()
            print(f"[SUCCESS] Password reset successfully for member_accounts ID {account_id}")
            print(f"  Username: {member_account[1]}")
            print(f"  Member ID: {member_account[2]}")
            print(f"  New password: {new_password}")
            return True
        
        # Check if it's an aawsa_user ID
        cursor.execute("SELECT user_id, username, payroll_number FROM aawsa_user WHERE user_id = %s", (account_id,))
        system_user = cursor.fetchone()
        
        if system_user:
            # Reset password for aawsa_user (uses werkzeug hash)
            password_hash = hash_password(new_password)
            cursor.execute("""
                UPDATE aawsa_user 
                SET password_hash = %s
                WHERE user_id = %s
            """, (password_hash, account_id))
            conn.commit()
            print(f"[SUCCESS] Password reset successfully for aawsa_user ID {account_id}")
            print(f"  Username: {system_user[1]}")
            print(f"  Payroll Number: {system_user[2]}")
            print(f"  New password: {new_password}")
            return True
        
        # If not found in either table
        print(f"[ERROR] ID {account_id} not found in member_accounts or aawsa_user tables")
        return False
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error resetting password: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("Resetting password for ID 83659...")
    reset_password()

