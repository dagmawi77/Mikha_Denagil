import mysql.connector
import hashlib

conn = mysql.connector.connect(
    host='localhost',
    port=3306,
    user='root',
    password='',
    database='aawsa_db',
    charset='utf8mb4'
)
cursor = conn.cursor(buffered=True)

password = "12345678"
password_hash = hashlib.sha256(password.encode()).hexdigest()

try:
    # Create/update dagmawi account
    cursor.execute("""
        INSERT INTO member_accounts (member_id, username, password_hash, account_status)
        SELECT 1, 'dagmawi', %s, 'Active'
        FROM DUAL
        WHERE EXISTS (SELECT 1 FROM member_registration WHERE id = 1)
        ON DUPLICATE KEY UPDATE 
            password_hash = VALUES(password_hash),
            account_status = 'Active'
    """, (password_hash,))
    
    conn.commit()
    print("SUCCESS! Member account ready!")
    print("")
    print("Login credentials:")
    print("  Username: dagmawi")
    print("  Password: 12345678")
    print("")
    
    # Show account info
    cursor.execute("""
        SELECT m.id, m.full_name, m.section_name
        FROM member_accounts ma
        JOIN member_registration m ON ma.member_id = m.id
        WHERE ma.username = 'dagmawi'
    """)
    info = cursor.fetchone()
    if info:
        print(f"  Member ID: {info[0]}")
        print(f"  Section: {info[2]}")
        print("")
        print("You can now login to the mobile app!")
    
except Exception as e:
    print(f"ERROR: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()

