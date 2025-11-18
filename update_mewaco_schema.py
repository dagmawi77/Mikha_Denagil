"""
Script to update mewaco_contributions table with Chapa payment columns
Run this script once to add payment tracking columns
"""
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database import get_db_connection

def update_mewaco_schema():
    """Add Chapa payment columns to mewaco_contributions table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("Updating mewaco_contributions table schema...")
        
        # Check if columns already exist
        cursor.execute("SHOW COLUMNS FROM mewaco_contributions LIKE 'tx_ref'")
        has_tx_ref = cursor.fetchone() is not None
        
        if not has_tx_ref:
            # Add new columns
            cursor.execute("""
                ALTER TABLE mewaco_contributions
                ADD COLUMN tx_ref VARCHAR(100) COMMENT 'Chapa transaction reference',
                ADD COLUMN chapa_reference VARCHAR(100) COMMENT 'Chapa payment reference',
                ADD COLUMN chapa_response TEXT COMMENT 'Full Chapa API response JSON',
                ADD COLUMN transaction_id VARCHAR(100) COMMENT 'Chapa transaction ID',
                ADD COLUMN payment_status VARCHAR(50) DEFAULT 'Pending' COMMENT 'Payment status: Pending, Completed, Paid, Failed',
                ADD COLUMN paid_at TIMESTAMP NULL COMMENT 'Payment completion timestamp',
                ADD COLUMN ip_address VARCHAR(45) COMMENT 'IP address of payment request',
                ADD COLUMN user_agent TEXT COMMENT 'User agent of payment request'
            """)
            
            # Add indexes (check if they exist first)
            try:
                cursor.execute("CREATE INDEX idx_tx_ref ON mewaco_contributions(tx_ref)")
            except Exception:
                pass  # Index already exists
            
            try:
                cursor.execute("CREATE INDEX idx_payment_status ON mewaco_contributions(payment_status)")
            except Exception:
                pass  # Index already exists
            
            try:
                cursor.execute("CREATE INDEX idx_chapa_ref ON mewaco_contributions(chapa_reference)")
            except Exception:
                pass  # Index already exists
            
            conn.commit()
            print("[OK] Successfully added payment columns to mewaco_contributions table")
        else:
            print("[INFO] Payment columns already exist, skipping...")
        
        # Show current schema
        cursor.execute("DESCRIBE mewaco_contributions")
        columns = cursor.fetchall()
        print("\nCurrent mewaco_contributions table columns:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
            
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error updating schema: {str(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    update_mewaco_schema()

