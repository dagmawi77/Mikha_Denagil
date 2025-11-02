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
        
        # Create role_routes junction table with CRUD permissions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_routes (
                role_id INT NOT NULL,
                route_id INT NOT NULL,
                can_create TINYINT(1) DEFAULT 0,
                can_read TINYINT(1) DEFAULT 1,
                can_update TINYINT(1) DEFAULT 0,
                can_delete TINYINT(1) DEFAULT 0,
                can_approve TINYINT(1) DEFAULT 0,
                can_export TINYINT(1) DEFAULT 0,
                PRIMARY KEY (role_id, route_id),
                FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE,
                FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Add CRUD permission columns to existing role_routes table if they don't exist
        crud_columns = [
            ('can_create', 'TINYINT(1) DEFAULT 0'),
            ('can_read', 'TINYINT(1) DEFAULT 1'),
            ('can_update', 'TINYINT(1) DEFAULT 0'),
            ('can_delete', 'TINYINT(1) DEFAULT 0'),
            ('can_approve', 'TINYINT(1) DEFAULT 0'),
            ('can_export', 'TINYINT(1) DEFAULT 0')
        ]
        
        for column_name, column_def in crud_columns:
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = 'role_routes' 
                    AND COLUMN_NAME = %s
                """, (Config.DB_NAME, column_name))
                
                if cursor.fetchone()[0] == 0:
                    cursor.execute(f"""
                        ALTER TABLE role_routes 
                        ADD COLUMN {column_name} {column_def}
                    """)
                    print(f"✓ Added {column_name} column to role_routes table")
            except Exception as e:
                print(f"⚠ Warning: Could not add {column_name} column: {e}")
        
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
        
        # Create inventory_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                item_name VARCHAR(255) NOT NULL COMMENT 'Item name/የእቃ ስም',
                category VARCHAR(100) NOT NULL COMMENT 'Category (Stationery, Electronics, etc.)',
                quantity INT NOT NULL DEFAULT 0 COMMENT 'Current quantity/አሁን ያለው መጠን',
                unit VARCHAR(50) NOT NULL COMMENT 'Unit (pieces, boxes, liters, etc.)',
                location VARCHAR(255) COMMENT 'Storage location/የማከማቻ ቦታ',
                supplier VARCHAR(255) COMMENT 'Supplier name/አቅራቢ',
                purchase_date DATE COMMENT 'Purchase date/የግዢ ቀን',
                unit_price DECIMAL(10,2) COMMENT 'Price per unit',
                min_stock_level INT DEFAULT 10 COMMENT 'Minimum stock alert level',
                description TEXT COMMENT 'Item description/መግለጫ',
                status VARCHAR(50) DEFAULT 'Active' COMMENT 'Active/Inactive/Discontinued',
                created_by VARCHAR(50) COMMENT 'User who created',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_category (category),
                INDEX idx_location (location),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Inventory items/የእቃ መዝገብ'
        """)
        
        # Create inventory_transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                item_id INT NOT NULL COMMENT 'Reference to inventory item',
                transaction_type VARCHAR(50) NOT NULL COMMENT 'Incoming/Outgoing/Adjustment',
                quantity INT NOT NULL COMMENT 'Quantity moved',
                transaction_date DATE NOT NULL COMMENT 'Transaction date',
                reference_number VARCHAR(100) COMMENT 'Invoice/Receipt number',
                responsible_user VARCHAR(100) COMMENT 'User responsible for transaction',
                recipient VARCHAR(255) COMMENT 'Who received (for outgoing)',
                purpose VARCHAR(255) COMMENT 'Purpose of transaction',
                notes TEXT COMMENT 'Additional notes',
                previous_quantity INT COMMENT 'Quantity before transaction',
                new_quantity INT COMMENT 'Quantity after transaction',
                created_by VARCHAR(50) COMMENT 'User who recorded',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE CASCADE,
                INDEX idx_item (item_id),
                INDEX idx_type (transaction_type),
                INDEX idx_date (transaction_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Inventory transactions/የእቃ እንቅስቃሴ'
        """)
        
        # Create fixed_assets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fixed_assets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                asset_name VARCHAR(255) NOT NULL COMMENT 'Asset name/የእቃ ስም',
                category VARCHAR(100) NOT NULL COMMENT 'Furniture, Electronics, Vehicle, etc.',
                purchase_date DATE NOT NULL COMMENT 'Purchase date/የግዢ ቀን',
                purchase_cost DECIMAL(15,2) NOT NULL COMMENT 'Purchase cost in Birr',
                current_location VARCHAR(255) COMMENT 'Current location/አሁን ያለበት ቦታ',
                condition_status VARCHAR(50) DEFAULT 'Good' COMMENT 'Good, Fair, Poor',
                assigned_department VARCHAR(100) COMMENT 'Department/section assigned to',
                assigned_user VARCHAR(100) COMMENT 'Specific user assigned to',
                serial_number VARCHAR(100) COMMENT 'Serial number or asset tag',
                useful_life_years INT DEFAULT 5 COMMENT 'Expected useful life in years',
                depreciation_method VARCHAR(50) DEFAULT 'Straight-Line' COMMENT 'Straight-Line, Declining, etc.',
                salvage_value DECIMAL(15,2) DEFAULT 0 COMMENT 'Estimated salvage value',
                accumulated_depreciation DECIMAL(15,2) DEFAULT 0 COMMENT 'Total depreciation',
                book_value DECIMAL(15,2) COMMENT 'Current book value',
                description TEXT COMMENT 'Asset description',
                status VARCHAR(50) DEFAULT 'Active' COMMENT 'Active, Disposed, Under Repair',
                disposal_date DATE COMMENT 'Date disposed if applicable',
                disposal_method VARCHAR(100) COMMENT 'Sold, Donated, Scrapped',
                disposal_value DECIMAL(15,2) COMMENT 'Disposal/sale value',
                created_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_category (category),
                INDEX idx_location (current_location),
                INDEX idx_department (assigned_department),
                INDEX idx_status (status),
                INDEX idx_serial (serial_number)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Fixed assets register/የቋሚ እቃ መዝገብ'
        """)
        
        # Create asset_movements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS asset_movements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                asset_id INT NOT NULL COMMENT 'Reference to fixed asset',
                movement_type VARCHAR(50) NOT NULL COMMENT 'Assignment, Relocation, Repair, Disposal',
                movement_date DATE NOT NULL COMMENT 'Movement date',
                from_location VARCHAR(255) COMMENT 'Previous location',
                to_location VARCHAR(255) COMMENT 'New location',
                from_department VARCHAR(100) COMMENT 'Previous department',
                to_department VARCHAR(100) COMMENT 'New department',
                from_user VARCHAR(100) COMMENT 'Previous user',
                to_user VARCHAR(100) COMMENT 'New user',
                responsible_person VARCHAR(100) COMMENT 'Person responsible for movement',
                condition_before VARCHAR(50) COMMENT 'Condition before movement',
                condition_after VARCHAR(50) COMMENT 'Condition after movement',
                repair_cost DECIMAL(10,2) COMMENT 'Cost if repair movement',
                remarks TEXT COMMENT 'Movement remarks/notes',
                created_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (asset_id) REFERENCES fixed_assets(id) ON DELETE CASCADE,
                INDEX idx_asset (asset_id),
                INDEX idx_type (movement_type),
                INDEX idx_date (movement_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Asset movement history/የእቃ እንቅስቃሴ ታሪክ'
        """)
        
        # Create departments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                department_name VARCHAR(255) NOT NULL COMMENT 'Department name/የመምሪያ ስም',
                department_code VARCHAR(50) UNIQUE COMMENT 'Department code',
                parent_department_id INT COMMENT 'For hierarchical structure',
                head_member_id INT COMMENT 'Department head (member reference)',
                description TEXT COMMENT 'Department description',
                status VARCHAR(50) DEFAULT 'Active' COMMENT 'Active/Inactive',
                created_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (head_member_id) REFERENCES member_registration(id) ON DELETE SET NULL,
                FOREIGN KEY (parent_department_id) REFERENCES departments(id) ON DELETE SET NULL,
                INDEX idx_dept_name (department_name),
                INDEX idx_dept_code (department_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Organization departments/መምሪያዎች'
        """)
        
        # Create positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS position_templates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                template_name VARCHAR(255) NOT NULL COMMENT 'Template name',
                category VARCHAR(100) COMMENT 'Template category (Ministry, Administrative, etc.)',
                position_title VARCHAR(255) NOT NULL COMMENT 'Position title',
                position_level VARCHAR(50) COMMENT 'Executive, Manager, Staff, etc.',
                responsibilities TEXT COMMENT 'Job responsibilities',
                position_type VARCHAR(50) DEFAULT 'Regular' COMMENT 'Regular, Temporary, Contract, Volunteer',
                is_leadership TINYINT(1) DEFAULT 0 COMMENT 'Is this a leadership position?',
                max_holders INT DEFAULT 1 COMMENT 'Maximum number of people who can hold this position',
                min_experience_years INT DEFAULT 0 COMMENT 'Minimum experience required',
                required_skills TEXT COMMENT 'Required skills and qualifications',
                description TEXT COMMENT 'Template description',
                is_active TINYINT(1) DEFAULT 1 COMMENT 'Is template active?',
                usage_count INT DEFAULT 0 COMMENT 'How many times this template was used',
                created_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_category (category),
                INDEX idx_level (position_level),
                INDEX idx_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Position templates for quick creation'
        """)
        
        # Add new columns to positions table if they don't exist
        try:
            cursor.execute("ALTER TABLE positions ADD COLUMN reporting_to INT COMMENT 'Reports to position ID'")
            cursor.execute("ALTER TABLE positions ADD COLUMN position_type VARCHAR(50) DEFAULT 'Regular' COMMENT 'Regular, Temporary, Contract, Volunteer'")
            cursor.execute("ALTER TABLE positions ADD COLUMN is_leadership TINYINT(1) DEFAULT 0 COMMENT 'Is this a leadership position?'")
            cursor.execute("ALTER TABLE positions ADD COLUMN max_holders INT DEFAULT 1 COMMENT 'Maximum number of people who can hold this position'")
            cursor.execute("ALTER TABLE positions ADD COLUMN min_experience_years INT DEFAULT 0 COMMENT 'Minimum experience required'")
            cursor.execute("ALTER TABLE positions ADD COLUMN required_skills TEXT COMMENT 'Required skills and qualifications'")
            cursor.execute("ALTER TABLE positions ADD COLUMN salary_range VARCHAR(100) COMMENT 'Salary range if applicable'")
            cursor.execute("ALTER TABLE positions ADD FOREIGN KEY (reporting_to) REFERENCES positions(id) ON DELETE SET NULL")
            cursor.execute("ALTER TABLE positions ADD INDEX idx_reporting (reporting_to)")
            cursor.execute("ALTER TABLE positions ADD INDEX idx_type (position_type)")
            print("✓ Enhanced positions table with new columns")
        except Exception as e:
            # Columns might already exist
            pass
        
        # Create positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                position_title VARCHAR(255) NOT NULL COMMENT 'Position title/የሥራ መደብ',
                department_id INT COMMENT 'Department this position belongs to',
                position_level VARCHAR(50) COMMENT 'Executive, Manager, Staff, etc.',
                responsibilities TEXT COMMENT 'Job responsibilities',
                reporting_to INT COMMENT 'Reports to position ID',
                position_type VARCHAR(50) DEFAULT 'Regular' COMMENT 'Regular, Temporary, Contract, Volunteer',
                is_leadership TINYINT(1) DEFAULT 0 COMMENT 'Is this a leadership position?',
                max_holders INT DEFAULT 1 COMMENT 'Maximum number of people who can hold this position',
                min_experience_years INT DEFAULT 0 COMMENT 'Minimum experience required',
                required_skills TEXT COMMENT 'Required skills and qualifications',
                salary_range VARCHAR(100) COMMENT 'Salary range if applicable',
                status VARCHAR(50) DEFAULT 'Active' COMMENT 'Active/Inactive',
                created_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL,
                FOREIGN KEY (reporting_to) REFERENCES positions(id) ON DELETE SET NULL,
                INDEX idx_position (position_title),
                INDEX idx_department (department_id),
                INDEX idx_level (position_level),
                INDEX idx_status (status),
                INDEX idx_reporting (reporting_to),
                INDEX idx_type (position_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Job positions/የሥራ መደቦች'
        """)
        
        # Create member_positions table (member-position assignment)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_positions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                member_id INT NOT NULL COMMENT 'Member reference',
                position_id INT NOT NULL COMMENT 'Position reference',
                department_id INT NOT NULL COMMENT 'Department reference',
                start_date DATE NOT NULL COMMENT 'Position start date',
                end_date DATE COMMENT 'Position end date (null if current)',
                is_current TINYINT(1) DEFAULT 1 COMMENT 'Is this the current position?',
                appointment_type VARCHAR(50) COMMENT 'Elected, Appointed, Volunteer',
                notes TEXT COMMENT 'Additional notes',
                created_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES member_registration(id) ON DELETE CASCADE,
                FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
                INDEX idx_member (member_id),
                INDEX idx_position (position_id),
                INDEX idx_department (department_id),
                INDEX idx_current (is_current)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Member position assignments/የአባላት የሥራ መደብ'
        """)
        
        # Create department_head_history table to track department leadership changes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS department_head_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                department_id INT NOT NULL COMMENT 'Department reference',
                member_id INT NOT NULL COMMENT 'Department head member reference',
                start_date DATE NOT NULL COMMENT 'Leadership start date',
                end_date DATE COMMENT 'Leadership end date (null if current)',
                is_current TINYINT(1) DEFAULT 1 COMMENT 'Is this the current head?',
                appointment_reason TEXT COMMENT 'Reason for appointment',
                termination_reason TEXT COMMENT 'Reason for end of leadership',
                created_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES member_registration(id) ON DELETE CASCADE,
                INDEX idx_department (department_id),
                INDEX idx_member (member_id),
                INDEX idx_current (is_current),
                INDEX idx_dates (start_date, end_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Department head history/የመምሪያ ኃላፊ ታሪክ'
        """)
        
        # Create member_accounts table for member portal/mobile app access
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                member_id INT NOT NULL UNIQUE COMMENT 'Member reference',
                username VARCHAR(50) NOT NULL UNIQUE COMMENT 'Login username',
                password_hash VARCHAR(255) NOT NULL COMMENT 'Hashed password',
                email VARCHAR(255) COMMENT 'Email address',
                phone VARCHAR(20) COMMENT 'Phone number',
                account_status VARCHAR(20) DEFAULT 'Active' COMMENT 'Active, Suspended, Inactive',
                is_verified TINYINT(1) DEFAULT 0 COMMENT 'Email/phone verified',
                last_login TIMESTAMP NULL COMMENT 'Last login timestamp',
                login_attempts INT DEFAULT 0 COMMENT 'Failed login attempts',
                locked_until TIMESTAMP NULL COMMENT 'Account locked until',
                password_reset_token VARCHAR(100) COMMENT 'Password reset token',
                password_reset_expires TIMESTAMP NULL COMMENT 'Token expiry',
                mobile_device_token TEXT COMMENT 'Firebase/push notification token',
                mobile_platform VARCHAR(20) COMMENT 'iOS, Android, etc',
                app_version VARCHAR(20) COMMENT 'Mobile app version',
                permissions TEXT COMMENT 'JSON array of member permissions',
                profile_photo_url VARCHAR(500) COMMENT 'Profile photo URL',
                created_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES member_registration(id) ON DELETE CASCADE,
                INDEX idx_username (username),
                INDEX idx_member (member_id),
                INDEX idx_status (account_status),
                INDEX idx_email (email),
                INDEX idx_phone (phone),
                INDEX idx_reset_token (password_reset_token)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Member portal accounts/የአባላት መለያዎች'
        """)
        
        # Create member_login_history table for security auditing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_login_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                member_account_id INT NOT NULL COMMENT 'Member account reference',
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Login timestamp',
                logout_time TIMESTAMP NULL COMMENT 'Logout timestamp',
                ip_address VARCHAR(50) COMMENT 'Login IP address',
                device_info TEXT COMMENT 'Device information',
                platform VARCHAR(50) COMMENT 'Web, iOS, Android',
                app_version VARCHAR(20) COMMENT 'App version used',
                location VARCHAR(255) COMMENT 'Login location',
                status VARCHAR(20) DEFAULT 'Success' COMMENT 'Success, Failed, Locked',
                failure_reason VARCHAR(255) COMMENT 'Reason for failure',
                session_duration INT COMMENT 'Session duration in seconds',
                FOREIGN KEY (member_account_id) REFERENCES member_accounts(id) ON DELETE CASCADE,
                INDEX idx_member_account (member_account_id),
                INDEX idx_login_time (login_time),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Member login history/የአባላት መግቢያ ታሪክ'
        """)
        
        # Create posts/announcements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                post_title VARCHAR(500) NOT NULL COMMENT 'Post title/ርዕስ',
                post_content TEXT NOT NULL COMMENT 'Post content/ይዘት',
                post_type VARCHAR(50) NOT NULL COMMENT 'Event, Announcement, General Info',
                target_section VARCHAR(100) COMMENT 'Target section (ክፍል) - All Sections, የሕፃናት ክፍል, etc.',
                target_medebe_id INT COMMENT 'Target medebe (ምድብ) if specific',
                start_date DATE COMMENT 'Post start date/የጅማሬ ቀን',
                end_date DATE COMMENT 'Post end date/የማብቂያ ቀን',
                attachment_path VARCHAR(500) COMMENT 'File attachment path',
                attachment_name VARCHAR(255) COMMENT 'Original filename',
                attachment_type VARCHAR(50) COMMENT 'File type (image, pdf, doc)',
                is_active TINYINT(1) DEFAULT 1 COMMENT 'Active status',
                status VARCHAR(20) DEFAULT 'Active' COMMENT 'Active, Expired, Draft',
                priority VARCHAR(20) DEFAULT 'Normal' COMMENT 'High, Normal, Low',
                views_count INT DEFAULT 0 COMMENT 'Number of views',
                created_by VARCHAR(50) COMMENT 'User who created the post',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (target_medebe_id) REFERENCES medebe(id) ON DELETE SET NULL,
                INDEX idx_post_type (post_type),
                INDEX idx_target_section (target_section),
                INDEX idx_target_medebe (target_medebe_id),
                INDEX idx_dates (start_date, end_date),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Posts and announcements/ማስታወቂያዎች'
        """)
        
        # Create post_read_status table to track which members have read posts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS post_read_status (
                id INT AUTO_INCREMENT PRIMARY KEY,
                post_id INT NOT NULL COMMENT 'Post reference',
                member_id INT NOT NULL COMMENT 'Member who read the post',
                read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When post was read',
                UNIQUE KEY unique_read (post_id, member_id),
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES member_registration(id) ON DELETE CASCADE,
                INDEX idx_post (post_id),
                INDEX idx_member (member_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Post read tracking/የተነበቡ ማስታወቂያዎች'
        """)
        
        conn.commit()
        print("✓ RBAC tables initialized/verified successfully")
        print("✓ Library tables initialized/verified successfully")
        print("✓ Inventory tables initialized/verified successfully")
        print("✓ Fixed Assets tables initialized/verified successfully")
        print("✓ Department & Position tables initialized/verified successfully")
        print("✓ Posts & Announcements tables initialized/verified successfully")
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
            ('Member Medebe Report', 'member_medebe_report', 'View member medebe assignments'),
            ('Inventory Management', 'manage_inventory', 'Manage inventory items'),
            ('Inventory Transactions', 'inventory_transactions', 'Record stock movements'),
            ('Inventory Stock Report', 'inventory_stock_report', 'View current stock levels'),
            ('Inventory Movement Report', 'inventory_movement_report', 'View stock transaction history'),
            ('Fixed Asset Register', 'manage_fixed_assets', 'Manage fixed assets register'),
            ('Asset Movement', 'asset_movements', 'Track asset assignments and relocations'),
            ('Asset Register Report', 'asset_register_report', 'View all assets with current status'),
            ('Asset Movement Report', 'asset_movement_report', 'View asset movement history'),
            ('Asset Depreciation Report', 'asset_depreciation_report', 'View asset depreciation analysis'),
            ('Department Management', 'manage_departments', 'Manage organizational departments'),
            ('Position Management', 'manage_positions', 'Manage job positions'),
            ('Member Position Assignment', 'assign_member_positions', 'Assign members to positions'),
            ('Organizational Chart', 'organizational_chart', 'View org structure and positions'),
            ('Posts Management', 'posts_management', 'Manage posts and announcements'),
            ('Posts Report', 'posts_report', 'View posts statistics and reports'),
            ('Member Posts View', 'member_posts_view', 'View posts assigned to member section')
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
        
        # Insert sample position templates if table is empty
        cursor.execute("SELECT COUNT(*) FROM position_templates")
        template_count = cursor.fetchone()[0]
        
        if template_count == 0:
            sample_templates = [
                ('Ministry Leadership', 'Ministry', 'Pastor', 'Executive', 'Lead spiritual services, provide pastoral care, oversee church operations', 'Regular', 1, 1, 5, 'Theology degree, pastoral experience, leadership skills', 'Spiritual leader of the congregation', 'ADMIN001'),
                ('Ministry Leadership', 'Ministry', 'Assistant Pastor', 'Manager', 'Assist pastor, lead specific ministries, provide pastoral support', 'Regular', 1, 1, 3, 'Theology background, ministry experience, communication skills', 'Support pastor in ministry duties', 'ADMIN001'),
                ('Ministry Leadership', 'Ministry', 'Youth Pastor', 'Manager', 'Lead youth ministry, organize youth activities, mentor young people', 'Regular', 1, 1, 2, 'Youth ministry experience, counseling skills, energetic personality', 'Dedicated youth ministry leader', 'ADMIN001'),
                ('Administrative', 'Administrative', 'Church Secretary', 'Staff', 'Handle correspondence, maintain records, assist with administrative tasks', 'Regular', 0, 1, 1, 'Administrative skills, computer literacy, organization', 'Administrative support role', 'ADMIN001'),
                ('Administrative', 'Administrative', 'Treasurer', 'Manager', 'Manage church finances, prepare budgets, handle financial records', 'Regular', 1, 1, 2, 'Accounting knowledge, financial management, integrity', 'Financial management role', 'ADMIN001'),
                ('Administrative', 'Administrative', 'Assistant Treasurer', 'Staff', 'Assist treasurer, handle daily financial transactions', 'Regular', 0, 1, 1, 'Basic accounting, attention to detail, honesty', 'Financial support role', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Sunday School Teacher', 'Staff', 'Teach Sunday school classes, prepare lessons, mentor children', 'Regular', 0, 5, 1, 'Teaching skills, patience, biblical knowledge', 'Children education ministry', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Worship Leader', 'Staff', 'Lead worship services, coordinate music ministry, train musicians', 'Regular', 0, 1, 2, 'Musical ability, leadership skills, worship experience', 'Music and worship ministry', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Choir Director', 'Staff', 'Direct choir, organize musical performances, train singers', 'Regular', 0, 1, 2, 'Musical training, conducting skills, organizational ability', 'Choir leadership role', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Deacon', 'Manager', 'Serve congregation, assist with church services, provide spiritual support', 'Regular', 1, 3, 2, 'Spiritual maturity, servant heart, leadership qualities', 'Spiritual service role', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Elder', 'Manager', 'Provide spiritual guidance, participate in church governance, mentor members', 'Regular', 1, 3, 3, 'Spiritual maturity, wisdom, leadership experience', 'Spiritual leadership role', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Evangelist', 'Staff', 'Conduct evangelistic activities, outreach programs, share gospel', 'Regular', 0, 2, 2, 'Evangelistic passion, communication skills, biblical knowledge', 'Outreach ministry role', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Mission Coordinator', 'Manager', 'Coordinate mission activities, organize outreach programs, manage volunteers', 'Regular', 1, 1, 2, 'Organizational skills, passion for missions, leadership', 'Mission ministry coordination', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Women Ministry Leader', 'Manager', 'Lead women ministry, organize women activities, provide spiritual support', 'Regular', 1, 1, 2, 'Leadership skills, women ministry experience, empathy', 'Women ministry leadership', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Men Ministry Leader', 'Manager', 'Lead men ministry, organize men activities, provide spiritual support', 'Regular', 1, 1, 2, 'Leadership skills, men ministry experience, mentorship', 'Men ministry leadership', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Children Ministry Leader', 'Manager', 'Lead children ministry, organize children activities, coordinate teachers', 'Regular', 1, 1, 2, 'Children ministry experience, patience, organizational skills', 'Children ministry leadership', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Youth Ministry Leader', 'Manager', 'Lead youth ministry, organize youth activities, mentor young people', 'Regular', 1, 1, 2, 'Youth ministry experience, mentorship skills, energy', 'Youth ministry leadership', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Prayer Ministry Leader', 'Staff', 'Lead prayer meetings, coordinate prayer activities, encourage prayer life', 'Regular', 0, 1, 1, 'Prayer life, spiritual maturity, organizational skills', 'Prayer ministry leadership', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Hospitality Coordinator', 'Staff', 'Coordinate hospitality, manage church events, welcome visitors', 'Regular', 0, 1, 1, 'Hospitality skills, organization, friendly personality', 'Hospitality and events coordination', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Usher', 'Volunteer', 'Welcome members and visitors, assist with seating, maintain order', 'Volunteer', 0, 5, 0, 'Friendly personality, helpful attitude, punctuality', 'Service and hospitality role', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Sound Technician', 'Staff', 'Operate sound equipment, maintain audio systems, support worship', 'Regular', 0, 1, 1, 'Technical skills, audio equipment knowledge, reliability', 'Technical support role', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Security Coordinator', 'Staff', 'Ensure church security, coordinate safety measures, manage security team', 'Regular', 0, 1, 2, 'Security awareness, leadership skills, responsibility', 'Security and safety role', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Maintenance Coordinator', 'Staff', 'Coordinate church maintenance, manage facilities, oversee repairs', 'Regular', 0, 1, 2, 'Maintenance skills, organizational ability, responsibility', 'Facilities management role', 'ADMIN001'),
                ('Ministry', 'Ministry', 'Library Coordinator', 'Staff', 'Manage church library, organize books, assist members with resources', 'Regular', 0, 1, 1, 'Organizational skills, book knowledge, helpful attitude', 'Library management role', 'ADMIN001')
            ]
            
            for template in sample_templates:
                cursor.execute("""
                    INSERT INTO position_templates (
                        template_name, category, position_title, position_level, 
                        responsibilities, position_type, is_leadership, max_holders, 
                        min_experience_years, required_skills, description, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, template)
            
            print("✓ Sample position templates inserted successfully")
        
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

