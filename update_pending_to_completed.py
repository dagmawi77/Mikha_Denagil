"""
Script to update all Pending donations to Completed status
Run this once to update existing pending donations
"""

from database import get_db_connection
from datetime import datetime

def update_pending_to_completed():
    """Update all pending donations to completed status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First, check how many pending donations exist
        cursor.execute("SELECT COUNT(*) FROM donations WHERE payment_status = 'Pending'")
        pending_count = cursor.fetchone()[0]
        print(f"Found {pending_count} donation(s) with Pending status")
        
        # Update all pending donations to completed
        cursor.execute("""
            UPDATE donations 
            SET payment_status = 'Completed',
                paid_at = COALESCE(paid_at, NOW()),
                updated_at = NOW()
            WHERE payment_status = 'Pending'
        """)
        
        updated_count = cursor.rowcount
        conn.commit()
        
        print(f"[OK] Successfully updated {updated_count} pending donation(s) to Completed status")
        
        # Show summary
        cursor.execute("""
            SELECT payment_status, COUNT(*) as count 
            FROM donations 
            GROUP BY payment_status
        """)
        results = cursor.fetchall()
        
        print("\nCurrent donation status summary:")
        for status, count in results:
            print(f"  {status}: {count}")
            
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error updating donations: {str(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("Updating pending donations to Completed status...")
    update_pending_to_completed()
    print("\nDone!")

