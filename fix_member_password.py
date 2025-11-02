"""
Fix member account password for mobile login
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
    # Update dagmawi account password to 12345678
    username = "dagmawi"
    password = "12345678"
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    cursor.execute("""
        UPDATE member_accounts 
        SET password_hash = %s, account_status = 'Active'
        WHERE username = %s
    """, (password_hash, username))
    
    if cursor.rowcount > 0:
        conn.commit()
        print(f"[OK] Password updated for username: {username}")
        print(f"\nYou can now login with:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        
        # Get member info
        cursor.execute("""
            SELECT m.full_name, m.section_name, ma.account_status
            FROM member_accounts ma
            JOIN member_registration m ON ma.member_id = m.id
            WHERE ma.username = %s
        """, (username,))
        info = cursor.fetchone()
        if info:
            print(f"\n  Member Name: {info[0]}")
            print(f"  Section: {info[1]}")
            print(f"  Account Status: {info[2]}")
    else:
        print(f"[ERROR] Username '{username}' not found!")
        
        # List all existing member accounts
        print("\nExisting member accounts:")
        cursor.execute("""
            SELECT ma.username, m.full_name, m.section_name
            FROM member_accounts ma
            JOIN member_registration m ON ma.member_id = m.id
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"  - {row[0]} | {row[1]} | {row[2]}")

except Exception as e:
    print(f"[ERROR] Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()

print("\n" + "="*50)
print("Done!")
print("="*50)

