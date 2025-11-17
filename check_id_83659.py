"""
Check what ID 83659 refers to in the database
"""
from database import get_db_connection

def check_id():
    """Check ID 83659 in various tables"""
    account_id = 83659
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"Checking ID {account_id} in various tables...\n")
    
    # Check member_accounts
    cursor.execute("SELECT id, username, member_id FROM member_accounts WHERE id = %s", (account_id,))
    result = cursor.fetchone()
    if result:
        print(f"[FOUND] member_accounts.id = {account_id}")
        print(f"  Username: {result[1]}")
        print(f"  Member ID: {result[2]}\n")
    else:
        print(f"[NOT FOUND] member_accounts.id = {account_id}\n")
    
    # Check aawsa_user
    cursor.execute("SELECT user_id, username, payroll_number FROM aawsa_user WHERE user_id = %s", (account_id,))
    result = cursor.fetchone()
    if result:
        print(f"[FOUND] aawsa_user.user_id = {account_id}")
        print(f"  Username: {result[1]}")
        print(f"  Payroll Number: {result[2]}\n")
    else:
        print(f"[NOT FOUND] aawsa_user.user_id = {account_id}\n")
    
    # Check member_registration
    cursor.execute("SELECT id, full_name, phone FROM member_registration WHERE id = %s", (account_id,))
    result = cursor.fetchone()
    if result:
        print(f"[FOUND] member_registration.id = {account_id}")
        print(f"  Full Name: {result[1]}")
        print(f"  Phone: {result[2]}\n")
        
        # Check if this member has an account
        cursor.execute("SELECT id, username FROM member_accounts WHERE member_id = %s", (account_id,))
        account = cursor.fetchone()
        if account:
            print(f"  -> Has member_accounts.id = {account[0]}")
            print(f"  -> Username: {account[1]}\n")
    else:
        print(f"[NOT FOUND] member_registration.id = {account_id}\n")
    
    # Check member_accounts by member_id
    cursor.execute("SELECT id, username, member_id FROM member_accounts WHERE member_id = %s", (account_id,))
    result = cursor.fetchone()
    if result:
        print(f"[FOUND] member_accounts.member_id = {account_id}")
        print(f"  Account ID: {result[0]}")
        print(f"  Username: {result[1]}\n")
    else:
        print(f"[NOT FOUND] member_accounts.member_id = {account_id}\n")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_id()

