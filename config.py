"""
Configuration settings for the application
"""
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # Flask settings
    SECRET_KEY = 'your_secret_key'  # Change this to a secure random key
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5001
    
    # MySQL Database settings
    DB_HOST = 'localhost'
    DB_PORT = 3306
    DB_USER = 'root'
    DB_PASSWORD = ''
    DB_NAME = 'aawsa_db'
    DB_CHARSET = 'utf8mb4'
    DB_COLLATION = 'utf8mb4_unicode_ci'
    
    # Billing Database settings (if different)
    BILLING_DB_HOST = '192.168.2.200'
    BILLING_DB_PORT = 3306
    BILLING_DB_USER = 'root'
    BILLING_DB_PASSWORD = ''
    BILLING_DB_NAME = 'aawsa_billing'
    
    # Upload settings
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp3', 'wav', 'm4a', 'mp4', 'avi', 'mov', 'doc', 'docx'}
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB max upload (for study materials with attachments)
    
    # Pagination
    ITEMS_PER_PAGE = 50
    
    # Session timeout (minutes)
    SESSION_TIMEOUT_MINUTES = 30

