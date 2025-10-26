"""
Utility functions used across the application
"""
from datetime import date, timedelta

def get_last_10_weeks_weekends():
    """
    Get the last 10 weekend dates (Saturdays and Sundays).
    Returns list of date strings in 'YYYY-MM-DD' format.
    """
    today = date.today()
    weekends = []
    days_back = 0
    
    while len(weekends) < 10:
        check_date = today - timedelta(days=days_back)
        # 5 = Saturday, 6 = Sunday
        if check_date.weekday() in [5, 6]:
            weekends.append(check_date.strftime('%Y-%m-%d'))
        days_back += 1
        
        # Safety check - don't go back more than 100 days
        if days_back > 100:
            break
    
    return list(reversed(weekends))  # Return chronological order

def get_members():
    """
    Get list of unique section names from member_registration table.
    Returns list of section names.
    """
    from database import get_db_connection
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT DISTINCT section_name FROM member_registration ORDER BY section_name")
        sections = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return sections
    except Exception as e:
        print(f"Error getting sections: {e}")
        return []

def allowed_file(filename, allowed_extensions=None):
    """
    Check if file extension is allowed.
    """
    if allowed_extensions is None:
        from config import Config
        allowed_extensions = Config.ALLOWED_EXTENSIONS
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

