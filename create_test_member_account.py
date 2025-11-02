"""
Create a test member account for mobile app login
"""
import mysql.connector
import hashlib
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Database connection
conn = mysql.connector.connect(
    host='localhost',
    port=3306,
    user='root',
    password='',
    database='aawsa_db',
    charset='utf8mb4'
)
cursor = conn.cursor(buffered=True)

try:
    # First, check if a test member exists in member_registration
    cursor.execute("SELECT id, full_name, section_name FROM member_registration LIMIT 1")
    member = cursor.fetchone()
    
    if member:
        member_id, full_name, section = member
        print(f"[OK] Found member: {full_name} (ID: {member_id}, Section: {section})")
        
        # Check if account already exists
        cursor.execute("SELECT id, username FROM member_accounts WHERE member_id = %s", (member_id,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"[OK] Account already exists: {existing[1]}")
            print(f"\nLogin with:")
            print(f"  Username: {existing[1]}")
            print(f"  Password: 12345678")
        else:
            # Create account for this member
            username = "dagmawi"
            password = "12345678"
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO member_accounts (
                    member_id, username, password_hash, account_status
                ) VALUES (%s, %s, %s, 'Active')
            """, (member_id, username, password_hash))
            
            conn.commit()
            print(f"[OK] Created member account successfully!")
            print(f"\nLogin with:")
            print(f"  Username: {username}")
            print(f"  Password: {password}")
            print(f"  Member: {full_name}")
            print(f"  Section: {section}")
    else:
        # No members found, create a test member first
        print("[ERROR] No members found in database!")
        print("\nCreating test member...")
        
        cursor.execute("""
            INSERT INTO member_registration (
                full_name, section_name, gender, phone, email
            ) VALUES (
                'Dagmawi Test', 'ወጣት ክፍል', 'ወንድ', '0911234567', 'test@example.com'
            )
        """)
        member_id = cursor.lastrowid
        conn.commit()
        
        print(f"[OK] Created test member: Dagmawi Test (ID: {member_id})")
        
        # Create account
        username = "dagmawi"
        password = "12345678"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute("""
            INSERT INTO member_accounts (
                member_id, username, password_hash, account_status
            ) VALUES (%s, %s, %s, 'Active')
        """, (member_id, username, password_hash))
        
        conn.commit()
        print(f"[OK] Created member account!")
        print(f"\nLogin with:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")

except Exception as e:
    print(f"[ERROR] Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()

print("\n" + "="*50)
print("Member account ready for mobile app login!")
print("="*50)

