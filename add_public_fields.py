"""
Script to add is_public fields to posts and studies tables
Run this script once to add public display functionality
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database import get_db_connection

def add_public_fields():
    """Add is_public columns to posts and studies tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("Adding is_public fields to posts and studies tables...")
        
        # Check if column exists in posts table
        cursor.execute("SHOW COLUMNS FROM posts LIKE 'is_public'")
        posts_has_field = cursor.fetchone() is not None
        
        if not posts_has_field:
            cursor.execute("""
                ALTER TABLE posts
                ADD COLUMN is_public TINYINT(1) DEFAULT 0 COMMENT 'Show on public website'
            """)
            print("[OK] Added is_public field to posts table")
        else:
            print("[INFO] is_public field already exists in posts table")
        
        # Check if column exists in studies table
        cursor.execute("SHOW COLUMNS FROM studies LIKE 'is_public'")
        studies_has_field = cursor.fetchone() is not None
        
        if not studies_has_field:
            cursor.execute("""
                ALTER TABLE studies
                ADD COLUMN is_public TINYINT(1) DEFAULT 0 COMMENT 'Show on public website'
            """)
            print("[OK] Added is_public field to studies table")
        else:
            print("[INFO] is_public field already exists in studies table")
        
        # Add indexes
        try:
            cursor.execute("CREATE INDEX idx_posts_public ON posts(is_public, status)")
            print("[OK] Added index for posts public queries")
        except Exception:
            print("[INFO] Index already exists for posts")
        
        try:
            cursor.execute("CREATE INDEX idx_studies_public ON studies(is_public, status)")
            print("[OK] Added index for studies public queries")
        except Exception:
            print("[INFO] Index already exists for studies")
        
        conn.commit()
        print("\n[SUCCESS] Database schema updated successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error updating schema: {str(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    add_public_fields()

