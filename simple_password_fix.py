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

# Password to set
password = "12345678"
password_hash = hashlib.sha256(password.encode()).hexdigest()

# Update ALL member accounts to use this password for testing
cursor.execute("""
    UPDATE member_accounts 
    SET password_hash = %s, account_status = 'Active'
""", (password_hash,))

conn.commit()

print(f"Updated {cursor.rowcount} member account(s)")
print(f"\nPassword hash: {password_hash}")
print(f"\nAll member accounts now use password: {password}")

# List all member accounts
cursor.execute("""
    SELECT ma.username, m.full_name, m.section_name, ma.account_status
    FROM member_accounts ma
    JOIN member_registration m ON ma.member_id = m.id
""")

print("\nMember Accounts:")
print("-" * 80)
for row in cursor.fetchall():
    print(f"Username: {row[0]:20} | Name: {row[1]:30} | Section: {row[2]}")

cursor.close()
conn.close()

print("-" * 80)
print("\nYou can now login to mobile app with any username above and password: 12345678")

