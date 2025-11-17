"""
Search for 83659 as username, payroll_number, or partial match
"""
from database import get_db_connection

def search_83659():
    """Search for 83659 in various fields"""
    search_term = "83659"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"Searching for '{search_term}' in various fields...\n")
    
    # Check member_accounts by username
    cursor.execute("SELECT id, username, member_id FROM member_accounts WHERE username LIKE %s", (f"%{search_term}%",))
    results = cursor.fetchall()
    if results:
        print(f"[FOUND] member_accounts.username containing '{search_term}':")
        for row in results:
            print(f"  ID: {row[0]}, Username: {row[1]}, Member ID: {row[2]}")
        print()
    else:
        print(f"[NOT FOUND] member_accounts.username containing '{search_term}'\n")
    
    # Check aawsa_user by username
    cursor.execute("SELECT user_id, username, payroll_number FROM aawsa_user WHERE username LIKE %s", (f"%{search_term}%",))
    results = cursor.fetchall()
    if results:
        print(f"[FOUND] aawsa_user.username containing '{search_term}':")
        for row in results:
            print(f"  User ID: {row[0]}, Username: {row[1]}, Payroll: {row[2]}")
        print()
    else:
        print(f"[NOT FOUND] aawsa_user.username containing '{search_term}'\n")
    
    # Check aawsa_user by payroll_number
    cursor.execute("SELECT user_id, username, payroll_number FROM aawsa_user WHERE payroll_number LIKE %s", (f"%{search_term}%",))
    results = cursor.fetchall()
    if results:
        print(f"[FOUND] aawsa_user.payroll_number containing '{search_term}':")
        for row in results:
            print(f"  User ID: {row[0]}, Username: {row[1]}, Payroll: {row[2]}")
        print()
    else:
        print(f"[NOT FOUND] aawsa_user.payroll_number containing '{search_term}'\n")
    
    # Check member_registration by phone
    cursor.execute("SELECT id, full_name, phone FROM member_registration WHERE phone LIKE %s", (f"%{search_term}%",))
    results = cursor.fetchall()
    if results:
        print(f"[FOUND] member_registration.phone containing '{search_term}':")
        for row in results[:5]:  # Limit to 5 results
            print(f"  Member ID: {row[0]}, Name: {row[1]}, Phone: {row[2]}")
        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more")
        print()
    else:
        print(f"[NOT FOUND] member_registration.phone containing '{search_term}'\n")
    
    # Show some sample IDs from each table
    print("Sample IDs from each table:")
    cursor.execute("SELECT id FROM member_accounts ORDER BY id DESC LIMIT 5")
    print(f"  member_accounts IDs (latest 5): {[row[0] for row in cursor.fetchall()]}")
    
    cursor.execute("SELECT user_id FROM aawsa_user ORDER BY user_id DESC LIMIT 5")
    print(f"  aawsa_user IDs (latest 5): {[row[0] for row in cursor.fetchall()]}")
    
    cursor.execute("SELECT id FROM member_registration ORDER BY id DESC LIMIT 5")
    print(f"  member_registration IDs (latest 5): {[row[0] for row in cursor.fetchall()]}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    search_83659()

