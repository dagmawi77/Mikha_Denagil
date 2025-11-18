"""
Script to configure Chapa test keys for donation system
Run this once to set up test credentials
"""

from database import get_db_connection
from config import Config

def setup_chapa_test_keys():
    """Set up Chapa test keys in donation_settings table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Chapa test credentials
        test_keys = {
            'chapa_public_key': 'CHAPUBK_TEST-L0hqsaiWfP8JXJMXBqFyRSRbyJHp2quS',
            'chapa_secret_key': 'CHASECK_TEST-Gm6uD4CijZ2RSUrYPWEyV2i56gHU1nQp',
            'chapa_encrypted_key': 'uFZFepcrugS4sGA7ofC6sX77',  # For webhook signature verification
            'callback_url': '',  # Will be auto-generated
            'redirect_url_after_payment': '/donation/thank-you'
        }
        
        print("Setting up Chapa test keys...")
        
        for key, value in test_keys.items():
            cursor.execute("""
                INSERT INTO donation_settings (setting_key, setting_value, description, updated_by)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    setting_value = VALUES(setting_value),
                    updated_by = VALUES(updated_by),
                    updated_at = CURRENT_TIMESTAMP
            """, (key, value, f'Chapa {key.replace("_", " ").title()}', 'SYSTEM'))
            print(f"[OK] Set {key}")
        
        conn.commit()
        print("\n[SUCCESS] Chapa test keys configured successfully!")
        print("\nYou can now test donations using:")
        print("  - Public Key: CHAPUBK_TEST-L0hqsaiWfP8JXJMXBqFyRSRbyJHp2quS")
        print("  - Secret Key: CHASECK_TEST-Gm6uD4CijZ2RSUrYPWEyV2i56gHU1nQp")
        print("\nNote: These are TEST keys. Use production keys for live donations.")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error setting up Chapa keys: {str(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    setup_chapa_test_keys()

