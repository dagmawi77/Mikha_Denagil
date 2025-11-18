"""
Diagnostic script to check user login credentials
Run this to verify user account and password format
"""
from database import get_db_connection
from auth import verify_password, hash_password

def check_user(payroll_number):
    """Check user account details"""
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)
    
    try:
        # Get user details
        cursor.execute("""
            SELECT u.payroll_number, u.username, u.email, u.password_hash, u.role_id, r.role_name 
            FROM aawsa_user u
            LEFT JOIN roles r ON u.role_id = r.role_id
            WHERE u.payroll_number = %s
        """, (payroll_number,))
        
        user = cursor.fetchone()
        
        if user:
            print(f"User found: {user[1]} ({user[0]})")
            print(f"Email: {user[2]}")
            print(f"Password hash: {user[3][:50]}..." if user[3] and len(user[3]) > 50 else f"Password hash: {user[3]}")
            print(f"Role ID: {user[4]}")
            print(f"Role Name: {user[5] if user[5] else 'No role assigned'}")
            
            # Test password
            test_password = input("\nEnter password to test: ")
            if user[3]:
                if verify_password(user[3], test_password):
                    print("✓ Password verification successful!")
                elif user[3] == test_password:
                    print("✓ Password matches (plain text)")
                else:
                    print("✗ Password verification failed")
                    print(f"  Stored hash starts with: {user[3][:20] if user[3] else 'None'}")
            else:
                print("⚠ No password hash found")
        else:
            print(f"✗ User with payroll number '{payroll_number}' not found")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    payroll = input("Enter payroll number to check: ")
    check_user(payroll)

