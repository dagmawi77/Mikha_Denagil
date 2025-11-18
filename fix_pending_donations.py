"""Update all Pending donations to Completed"""
from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

try:
    cursor.execute("UPDATE donations SET payment_status = 'Completed', paid_at = COALESCE(paid_at, NOW()), updated_at = NOW() WHERE payment_status = 'Pending'")
    count = cursor.rowcount
    conn.commit()
    print(f"Updated {count} donations from Pending to Completed")
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()

