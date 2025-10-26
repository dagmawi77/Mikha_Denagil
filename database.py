"""
Database connection and utility functions
"""
import mysql.connector
from mysql.connector import Error as MySQLError
from datetime import date
from config import Config

def test_db_connection():
    """
    Test if MySQL database is reachable.
    Returns (success: bool, message: str)
    """
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset=Config.DB_CHARSET,
            collation=Config.DB_COLLATION
        )
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return True, "MySQL database connection successful"
    except MySQLError as e:
        return False, f"MySQL error {e.errno}: {e.msg}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

def get_db_connection():
    """
    Create connection to local MySQL database.
    Much simpler than Oracle - no timezone or listener issues!
    """
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset=Config.DB_CHARSET,
            collation=Config.DB_COLLATION,
            autocommit=False
        )
        return conn
    except MySQLError as e:
        if e.errno == 2003:
            raise Exception(f"MySQL server is not running on {Config.DB_HOST}:{Config.DB_PORT}. Please start MySQL service.")
        elif e.errno == 1045:
            raise Exception(f"MySQL access denied. Check username/password: {Config.DB_USER}/(empty)")
        elif e.errno == 1049:
            raise Exception(f"MySQL database '{Config.DB_NAME}' does not exist. Please run the setup script first.")
        else:
            raise Exception(f"MySQL connection error {e.errno}: {e.msg}")
    except Exception as e:
        raise Exception(f"Unable to connect to MySQL database: {str(e)}")

def get_db_connection_billing():
    """
    Create connection to billing MySQL database on remote server.
    """
    try:
        conn = mysql.connector.connect(
            host=Config.BILLING_DB_HOST,
            port=Config.BILLING_DB_PORT,
            user=Config.BILLING_DB_USER,
            password=Config.BILLING_DB_PASSWORD,
            database=Config.BILLING_DB_NAME,
            charset=Config.DB_CHARSET,
            collation=Config.DB_COLLATION,
            autocommit=False
        )
        return conn
    except MySQLError as e:
        if e.errno == 2003:
            raise Exception(f"Cannot connect to billing server at {Config.BILLING_DB_HOST}:{Config.BILLING_DB_PORT}")
        elif e.errno == 1045:
            raise Exception(f"Billing database access denied. Check credentials.")
        elif e.errno == 1049:
            raise Exception(f"Billing database '{Config.BILLING_DB_NAME}' does not exist.")
        else:
            raise Exception(f"Billing DB connection error {e.errno}: {e.msg}")
    except Exception as e:
        raise Exception(f"Unable to connect to billing database: {str(e)}")

def initialize_rbac_tables():
    """
    Initialize RBAC (Role-Based Access Control) tables if they don't exist.
    This creates the roles, routes, and role_routes tables.
    """
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"⚠ WARNING: Cannot initialize RBAC tables - {str(e)}")
        print("⚠ The application will start but database features won't work until the database is available.")
        return False
    
    cursor = conn.cursor(buffered=True)
    
    try:
        # Create roles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                role_id INT AUTO_INCREMENT PRIMARY KEY,
                role_name VARCHAR(100) NOT NULL UNIQUE,
                description VARCHAR(255)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create routes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS routes (
                route_id INT AUTO_INCREMENT PRIMARY KEY,
                route_name VARCHAR(100) NOT NULL UNIQUE,
                endpoint VARCHAR(255) NOT NULL UNIQUE,
                description VARCHAR(255)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create role_routes junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_routes (
                role_id INT NOT NULL,
                route_id INT NOT NULL,
                PRIMARY KEY (role_id, route_id),
                FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE,
                FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Check if aawsa_user table exists and add role_id column if needed
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'aawsa_user' 
            AND COLUMN_NAME = 'role_id'
        """, (Config.DB_NAME,))
        result = cursor.fetchone()
        if result and result[0] == 0:
            cursor.execute("""
                ALTER TABLE aawsa_user 
                ADD COLUMN role_id INT,
                ADD CONSTRAINT fk_user_role 
                FOREIGN KEY (role_id) REFERENCES roles(role_id)
            """)
        # Create library_books table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS library_books (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(500) NOT NULL COMMENT 'Book title/መፅሀፍ ርዕስ',
                author VARCHAR(255) NOT NULL COMMENT 'Author name/ደራሲ ስም',
                category VARCHAR(100) COMMENT 'Book category/ምድብ',
                isbn VARCHAR(50) UNIQUE COMMENT 'ISBN number',
                publisher VARCHAR(255) COMMENT 'Publisher name/አሳታሚ',
                publication_year INT COMMENT 'Publication year/የታተመበት ዓመት',
                language VARCHAR(50) DEFAULT 'Amharic' COMMENT 'Book language/ቋንቋ',
                total_copies INT DEFAULT 1 COMMENT 'Total number of copies/ጠቅላላ ቅጂዎች',
                available_copies INT DEFAULT 1 COMMENT 'Available copies/ለመበደር የሚገኙ',
                borrowed_copies INT DEFAULT 0 COMMENT 'Currently borrowed/የተበደሩ',
                shelf_location VARCHAR(100) COMMENT 'Shelf location/የመደርደሪያ አድራሻ',
                description TEXT COMMENT 'Book description/መግለጫ',
                cover_image VARCHAR(255) COMMENT 'Cover image path',
                status VARCHAR(20) DEFAULT 'Active' COMMENT 'Book status',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_by VARCHAR(50) COMMENT 'User who added the book',
                INDEX idx_title (title(255)),
                INDEX idx_author (author),
                INDEX idx_category (category),
                INDEX idx_isbn (isbn),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create book_borrowing table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS book_borrowing (
                id INT AUTO_INCREMENT PRIMARY KEY,
                member_id INT NOT NULL COMMENT 'Member who borrowed',
                book_id INT NOT NULL COMMENT 'Book that was borrowed',
                borrow_date DATE NOT NULL COMMENT 'Date borrowed',
                due_date DATE NOT NULL COMMENT 'Due date for return',
                return_date DATE COMMENT 'Actual return date',
                status VARCHAR(20) DEFAULT 'Borrowed' COMMENT 'Status: Borrowed, Returned, Overdue',
                notes TEXT COMMENT 'Additional notes',
                borrowed_by VARCHAR(50) COMMENT 'Staff who processed the borrowing',
                returned_to VARCHAR(50) COMMENT 'Staff who processed the return',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES member_registration(id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES library_books(id) ON DELETE CASCADE,
                INDEX idx_member (member_id),
                INDEX idx_book (book_id),
                INDEX idx_status (status),
                INDEX idx_borrow_date (borrow_date),
                INDEX idx_due_date (due_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Book borrowing transactions'
        """)
        
        # Create mewaco_types table (Contribution Types)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mewaco_types (
                id INT AUTO_INCREMENT PRIMARY KEY,
                type_name VARCHAR(255) NOT NULL UNIQUE COMMENT 'Contribution type name',
                description TEXT COMMENT 'Type description',
                default_amount DECIMAL(10, 2) DEFAULT 0.00 COMMENT 'Default contribution amount in Birr',
                status VARCHAR(20) DEFAULT 'Active' COMMENT 'Active or Inactive',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_by VARCHAR(50),
                INDEX idx_type_name (type_name),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MEWACO contribution types'
        """)
        
        # Create mewaco_contributions table (Monthly Contributions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mewaco_contributions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                member_id INT NOT NULL COMMENT 'Contributing member',
                mewaco_type_id INT NOT NULL COMMENT 'Contribution type',
                contribution_date DATE NOT NULL COMMENT 'Date of contribution',
                amount DECIMAL(10, 2) NOT NULL COMMENT 'Contribution amount in Birr',
                payment_method VARCHAR(50) DEFAULT 'Cash' COMMENT 'Payment method: Cash, Bank Transfer, Mobile Money',
                receipt_number VARCHAR(100) COMMENT 'Receipt/transaction number',
                notes TEXT COMMENT 'Additional notes',
                recorded_by VARCHAR(50) COMMENT 'Staff who recorded',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES member_registration(id) ON DELETE CASCADE,
                FOREIGN KEY (mewaco_type_id) REFERENCES mewaco_types(id) ON DELETE CASCADE,
                INDEX idx_member (member_id),
                INDEX idx_type (mewaco_type_id),
                INDEX idx_date (contribution_date),
                INDEX idx_receipt (receipt_number)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Member contributions'
        """)
        
        # Create medebe (sub-sections) table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medebe (
                id INT AUTO_INCREMENT PRIMARY KEY,
                medebe_name VARCHAR(255) NOT NULL COMMENT 'Sub-section name/ምድብ ስም',
                section_name VARCHAR(100) NOT NULL COMMENT 'Main section/የክፍል ስም',
                description TEXT COMMENT 'Description/ማብራሪያ',
                created_date DATE NOT NULL COMMENT 'Date created/ቀን የተፈጠረበት',
                created_by VARCHAR(50) COMMENT 'Staff who created',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_section (section_name),
                INDEX idx_medebe_name (medebe_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Sub-sections (Medebe) under main sections'
        """)
        
        # Create member_medebe_assignment table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_medebe_assignment (
                id INT AUTO_INCREMENT PRIMARY KEY,
                member_id INT NOT NULL COMMENT 'Member ID',
                medebe_id INT NOT NULL COMMENT 'Medebe ID',
                section_name VARCHAR(100) NOT NULL COMMENT 'Main section for validation',
                assigned_date DATE NOT NULL COMMENT 'Date assigned',
                assigned_by VARCHAR(50) COMMENT 'Staff who assigned',
                assignment_method VARCHAR(50) DEFAULT 'Manual' COMMENT 'Manual or Auto',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_member_assignment (member_id),
                FOREIGN KEY (member_id) REFERENCES member_registration(id) ON DELETE CASCADE,
                FOREIGN KEY (medebe_id) REFERENCES medebe(id) ON DELETE CASCADE,
                INDEX idx_medebe (medebe_id),
                INDEX idx_section (section_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Member to Medebe assignments'
        """)
        
        conn.commit()
        print("✓ RBAC tables initialized/verified successfully")
        print("✓ Library tables initialized/verified successfully")
        return True
    except Exception as e:
        conn.rollback()
        print(f"✗ Error initializing RBAC tables: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def initialize_default_roles_and_routes():
    """
    Initialize default roles and routes for the application.
    """
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"⚠ WARNING: Cannot initialize default roles and routes - {str(e)}")
        print("⚠ The application will start but RBAC features won't work until the database is available.")
        return False
    
    cursor = conn.cursor(buffered=True)
    
    try:
        # Insert default roles
        default_roles = [
            ('Super Admin', 'Full system access'),
            ('Finance', 'Finance and billing access'),
            ('Customer Service', 'Customer service and support'),
            ('Branch Manager', 'Branch management access'),
            ('Data Entry', 'Data entry access only'),
            ('Report Viewer', 'Read-only report access')
        ]
        
        for role_name, description in default_roles:
            cursor.execute(
                "INSERT IGNORE INTO roles (role_name, description) VALUES (%s, %s)",
                (role_name, description)
            )
        
        # Insert default routes
        default_routes = [
            ('Dashboard', 'navigation', 'Main dashboard'),
            ('User Management', 'user_management', 'Manage users'),
            ('Role Management', 'manage_roles', 'Manage roles'),
            ('Route Management', 'manage_routes', 'Manage routes'),
            ('Member Management', 'manage_members', 'Manage members'),
            ('Member Report', 'member_report', 'View comprehensive member reports'),
            ('Upload Members', 'upload_member_registration', 'Upload member registrations'),
            ('Attendance', 'attendance', 'Mark attendance'),
            ('Attendance Report', 'attendance_report', 'View attendance reports'),
            ('Library Management', 'manage_books', 'Manage library books'),
            ('Borrow Management', 'borrow_management', 'Manage book borrowing'),
            ('Book Report', 'book_report', 'View library book reports'),
            ('Borrow Report', 'borrow_report', 'View borrowing reports'),
            ('MEWACO Types', 'mewaco_types', 'Manage contribution types'),
            ('Monthly Contributions', 'monthly_contributions', 'Bulk monthly contribution collection'),
            ('Contribution Report', 'contribution_report_monthly', 'Monthly contribution reports'),
            ('Member Contribution Summary', 'member_contribution_summary', 'Member contribution history'),
            ('Medebe Management', 'medebe_management', 'Manage sub-sections (medebe)'),
            ('Member Medebe Assignment', 'member_medebe_assignment', 'Assign members to medebe'),
            ('Medebe Report', 'medebe_report', 'View medebe statistics and reports'),
            ('Member Medebe Report', 'member_medebe_report', 'View member medebe assignments')
        ]
        
        for route_name, endpoint, description in default_routes:
            cursor.execute(
                "INSERT IGNORE INTO routes (route_name, endpoint, description) VALUES (%s, %s, %s)",
                (route_name, endpoint, description)
            )
        
        # Give Super Admin access to all routes
        cursor.execute("""
            INSERT IGNORE INTO role_routes (role_id, route_id)
            SELECT r.role_id, rt.route_id
            FROM roles r
            CROSS JOIN routes rt
            WHERE r.role_name = 'Super Admin'
        """)
        
        # Insert sample library books if table is empty
        cursor.execute("SELECT COUNT(*) FROM library_books")
        book_count = cursor.fetchone()[0]
        
        if book_count == 0:
            sample_books = [
                ('መጽሐፈ ቅዱስ - Holy Bible', 'Various Authors', 'Spiritual', '978-0-123456-78-9', 
                 'Ethiopian Orthodox Church', 2020, 'Amharic', 10, 8, 0, 'A-001', 
                 'Complete Ethiopian Orthodox Tewahedo Bible in Amharic', None, 'Active', 'ADMIN001'),
                ('ድንግል ማርያም - Virgin Mary', 'Saint Ephrem', 'Spiritual', '978-0-234567-89-0',
                 'Tinsae Publishing', 2019, 'Amharic', 5, 4, 1, 'A-002',
                 'Book about the life and miracles of Virgin Mary', None, 'Active', 'ADMIN001'),
                ('የመንፈስ ቅዱስ ስጦታዎች', 'Abune Paulos', 'Spiritual', '978-0-345678-90-1',
                 'Mahibere Kidusan', 2021, 'Amharic', 8, 6, 2, 'A-003',
                 'Teachings about the gifts of the Holy Spirit', None, 'Active', 'ADMIN001'),
                ('ሕይወት በክርስቶስ', 'Fr. Daniel Kibret', 'Spiritual', '978-0-456789-01-2',
                 'Ethiopian Publishing House', 2022, 'Amharic', 12, 10, 2, 'A-004',
                 'Living a Christian life in modern times', None, 'Active', 'ADMIN001'),
                ('የልጆች መፅሐፍ ቅዱስ', 'Sunday School Committee', 'Children', '978-0-567890-12-3',
                 'Sunday School Press', 2020, 'Amharic', 20, 18, 2, 'B-001',
                 'Bible stories for children with illustrations', None, 'Active', 'ADMIN001'),
                ('ታሪክ የኢትዮጵያ ኦርቶዶክስ ተዋሕዶ ቤተ ክርስቲያን', 'Dr. Sergew Hable Selassie', 'History', '978-0-678901-23-4',
                 'Addis Ababa University', 2018, 'Amharic', 6, 5, 1, 'C-001',
                 'History of Ethiopian Orthodox Tewahedo Church', None, 'Active', 'ADMIN001'),
                ('የጸሎት መፅሐፍ', 'Traditional', 'Prayer', '978-0-789012-34-5',
                 'Church Publishing', 2021, 'Amharic', 15, 12, 3, 'A-005',
                 'Collection of Orthodox prayers and supplications', None, 'Active', 'ADMIN001'),
                ('መድኃኔዓለም', 'Traditional Authors', 'Spiritual', '978-0-890123-45-6',
                 'Tinsae Publishing', 2019, 'Amharic', 7, 5, 2, 'A-006',
                 'Book about Jesus Christ the Savior', None, 'Active', 'ADMIN001'),
                ('የወጣቶች መምሪያ', 'Youth Committee', 'Youth', '978-0-901234-56-7',
                 'Youth Ministry Press', 2023, 'Amharic', 10, 9, 1, 'B-002',
                 'Guidance and teachings for Orthodox youth', None, 'Active', 'ADMIN001'),
                ('ቅዱስ ቁርባን', 'Fr. Yared Tilahun', 'Liturgy', '978-0-012345-67-8',
                 'Liturgy Press', 2020, 'Amharic', 8, 7, 1, 'A-007',
                 'Understanding the Holy Eucharist', None, 'Active', 'ADMIN001')
            ]
            
            for book in sample_books:
                cursor.execute("""
                    INSERT INTO library_books (
                        title, author, category, isbn, publisher, publication_year,
                        language, total_copies, available_copies, borrowed_copies,
                        shelf_location, description, cover_image, status, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, book)
            
            print("✓ Sample library books inserted successfully")
        
        # Insert sample borrowing data if table is empty
        cursor.execute("SELECT COUNT(*) FROM book_borrowing")
        borrow_count = cursor.fetchone()[0]
        
        if borrow_count == 0:
            # Get some member IDs and book IDs for sample data
            cursor.execute("SELECT id FROM member_registration LIMIT 5")
            member_ids = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT id FROM library_books LIMIT 5")
            book_ids = [row[0] for row in cursor.fetchall()]
            
            if member_ids and book_ids:
                from datetime import datetime, timedelta
                today = datetime.now().date()
                
                sample_borrows = [
                    (member_ids[0], book_ids[0], today - timedelta(days=10), today + timedelta(days=4), None, 'Borrowed', 'Regular borrowing', 'ADMIN001'),
                    (member_ids[1], book_ids[1], today - timedelta(days=20), today - timedelta(days=6), None, 'Overdue', 'Needs follow-up', 'ADMIN001'),
                    (member_ids[2], book_ids[2], today - timedelta(days=30), today - timedelta(days=16), today - timedelta(days=3), 'Returned', 'Returned on time', 'ADMIN001'),
                    (member_ids[0], book_ids[3], today - timedelta(days=5), today + timedelta(days=9), None, 'Borrowed', '', 'ADMIN001'),
                    (member_ids[3], book_ids[4], today - timedelta(days=15), today - timedelta(days=1), None, 'Overdue', 'Follow-up required', 'ADMIN001')
                ]
                
                for borrow in sample_borrows:
                    cursor.execute("""
                        INSERT INTO book_borrowing (
                            member_id, book_id, borrow_date, due_date, return_date, 
                            status, notes, borrowed_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, borrow)
                
                print("✓ Sample borrowing transactions inserted successfully")
        
        # Insert sample MEWACO types if table is empty
        cursor.execute("SELECT COUNT(*) FROM mewaco_types")
        mewaco_type_count = cursor.fetchone()[0]
        
        if mewaco_type_count == 0:
            sample_types = [
                ('General Monthly Contribution', 'Regular monthly church contribution', 200.00, 'Active', 'ADMIN001'),
                ('Building Support', 'Contribution for church building projects', 500.00, 'Active', 'ADMIN001'),
                ('Charity Fund', 'Support for charitable activities', 150.00, 'Active', 'ADMIN001'),
                ('Special Offering', 'Special occasions and holidays', 300.00, 'Active', 'ADMIN001'),
                ('Youth Ministry Fund', 'Support for youth programs and activities', 100.00, 'Active', 'ADMIN001'),
                ('Sunday School Support', 'Support for children education programs', 100.00, 'Active', 'ADMIN001')
            ]
            
            for mtype in sample_types:
                cursor.execute("""
                    INSERT INTO mewaco_types (
                        type_name, description, default_amount, status, created_by
                    ) VALUES (%s, %s, %s, %s, %s)
                """, mtype)
            
            print("✓ Sample MEWACO types inserted successfully")
        
        # Insert sample medebe (sub-sections) if table is empty
        cursor.execute("SELECT COUNT(*) FROM medebe")
        medebe_count = cursor.fetchone()[0]
        
        if medebe_count == 0:
            sample_medebe = [
                ('የመጀመሪያ ምድብ', 'የሕፃናት ክፍል', 'Children first group', date.today(), 'ADMIN001'),
                ('የሁለተኛ ምድብ', 'የሕፃናት ክፍል', 'Children second group', date.today(), 'ADMIN001'),
                ('የመጀመሪያ ምድብ', 'ማህከላዊያን ክፍል', 'Middle-aged first group', date.today(), 'ADMIN001'),
                ('የሁለተኛ ምድብ', 'ማህከላዊያን ክፍል', 'Middle-aged second group', date.today(), 'ADMIN001'),
                ('የመጀመሪያ ምድብ', 'ወጣት ክፍል', 'Youth first group', date.today(), 'ADMIN001'),
                ('የሁለተኛ ምድብ', 'ወጣት ክፍል', 'Youth second group', date.today(), 'ADMIN001'),
                ('የሦስተኛ ምድብ', 'ወጣት ክፍል', 'Youth third group', date.today(), 'ADMIN001'),
                ('የመጀመሪያ ምድብ', 'ወላጅ ክፍል', 'Parent first group', date.today(), 'ADMIN001'),
                ('የሁለተኛ ምድብ', 'ወላጅ ክፍል', 'Parent second group', date.today(), 'ADMIN001'),
                ('የሦስተኛ ምድብ', 'ወላጅ ክፍል', 'Parent third group', date.today(), 'ADMIN001'),
            ]
            
            for medebe in sample_medebe:
                cursor.execute("""
                    INSERT INTO medebe (
                        medebe_name, section_name, description, created_date, created_by
                    ) VALUES (%s, %s, %s, %s, %s)
                """, medebe)
            
            print("✓ Sample medebe (sub-sections) inserted successfully")
        
        conn.commit()
        print("✓ Default roles and routes initialized successfully")
        return True
    except Exception as e:
        conn.rollback()
        print(f"✗ Error initializing default roles and routes: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

