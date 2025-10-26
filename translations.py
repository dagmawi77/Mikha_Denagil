"""
Bilingual Translation System for Amharic and English
"""

TRANSLATIONS = {
    # Navigation & Menu
    'dashboard': {'am': 'ዳሽቦርድ', 'en': 'Dashboard'},
    'member_management': {'am': 'አባላት ማስተዳደሪያ', 'en': 'Member Management'},
    'member_registration': {'am': 'አባላት መመዝገቢያ', 'en': 'Member Registration'},
    'member_report': {'am': 'የአባላት ሪፖርት', 'en': 'Member Report'},
    'bulk_upload': {'am': 'አባላት Upload ማድረጊያ', 'en': 'Bulk Member Upload'},
    'attendance': {'am': 'አባላት (Attendance)', 'en': 'Attendance'},
    'attendance_report': {'am': 'የአቴንዳንስ ሪፖርት', 'en': 'Attendance Report'},
    'reports': {'am': 'ሪፖርት', 'en': 'Reports'},
    'library': {'am': 'መፅሀፍት ቤት', 'en': 'Library'},
    'book_registration': {'am': 'መፅሀፍት መመዝገቢያ', 'en': 'Book Registration'},
    'borrow_management': {'am': 'መዋስ አስተዳደር', 'en': 'Borrow Management'},
    'book_report': {'am': 'መፅሀፍት ሪፖርት', 'en': 'Book Report'},
    'borrow_report': {'am': 'መዋስ ሪፖርት', 'en': 'Borrow Report'},
    'mewaco': {'am': 'መዋጮ', 'en': 'Contribution (MEWACO)'},
    'contribution_types': {'am': 'የመዋጮ አይነቶች', 'en': 'Contribution Types'},
    'monthly_contribution': {'am': 'የወር መዋጮ አሰባሰብ', 'en': 'Monthly Contribution'},
    'monthly_report': {'am': 'የወር መዋጮ ሪፖርት', 'en': 'Monthly Report'},
    'member_contribution': {'am': 'የአባላት መዋጮ ማጠቃለያ', 'en': 'Member Contribution Summary'},
    'section_medebe': {'am': 'ምድብ', 'en': 'Section & Medebe'},
    'medebe_management': {'am': 'ምድብ አስተዳደር', 'en': 'Medebe Management'},
    'member_assignment': {'am': 'የአባላት ምድብ መመደቢያ', 'en': 'Member Assignment'},
    'medebe_report': {'am': 'የምድብ ሪፖርት', 'en': 'Medebe Report'},
    'member_medebe_report': {'am': 'የአባላት ምድብ ሪፖርት', 'en': 'Member-Medebe Report'},
    'user_management': {'am': 'የተጠቃሚ አስተዳደር', 'en': 'User Management'},
    'manage_roles': {'am': 'የሚና አስተዳደር', 'en': 'Manage Roles'},
    'manage_routes': {'am': 'የመንገድ አስተዳደር', 'en': 'Manage Routes'},
    
    # Organization Module
    'organization': {'am': 'አደረጃጀት', 'en': 'Organization'},
    'departments': {'am': 'መምሪያዎች', 'en': 'Departments'},
    'positions': {'am': 'የሥራ መደቦች', 'en': 'Positions'},
    'assign_positions': {'am': 'መደብ መመደቢያ', 'en': 'Assign Positions'},
    'org_chart': {'am': 'አደረጃጀት ገበታ', 'en': 'Organizational Chart'},
    'department_management': {'am': 'የመምሪያ አስተዳደር', 'en': 'Department Management'},
    'position_management': {'am': 'የሥራ መደብ አስተዳደር', 'en': 'Position Management'},
    'dynamic_position_management': {'am': 'የተለዋዋጭ የሥራ መደብ አስተዳደር', 'en': 'Dynamic Position Management'},
    
    # Position Related
    'position_title': {'am': 'የሥራ መደብ ርዕስ', 'en': 'Position Title'},
    'position_level': {'am': 'የሥራ መደብ ደረጃ', 'en': 'Position Level'},
    'position_type': {'am': 'የሥራ መደብ አይነት', 'en': 'Position Type'},
    'reporting_to': {'am': 'ሪፖርት የሚያደርግበት', 'en': 'Reports To'},
    'max_holders': {'am': 'ከፍተኛ ያዢዎች', 'en': 'Maximum Holders'},
    'min_experience': {'am': 'ዝቅተኛ ልምድ', 'en': 'Minimum Experience'},
    'required_skills': {'am': 'የሚያስፈልጉ ክህሎቶች', 'en': 'Required Skills'},
    'responsibilities': {'am': 'ኃላፊነቶች', 'en': 'Responsibilities'},
    'is_leadership': {'am': 'የአመራር ሥራ ነው', 'en': 'Is Leadership Position'},
    'salary_range': {'am': 'የደመወዝ ክልል', 'en': 'Salary Range'},
    'executive': {'am': 'አስፈፃሚ', 'en': 'Executive'},
    'manager': {'am': 'አስተዳዳሪ', 'en': 'Manager'},
    'coordinator': {'am': 'አስተባባሪ', 'en': 'Coordinator'},
    'staff': {'am': 'ሰራተኛ', 'en': 'Staff'},
    'volunteer': {'am': 'በጎ ፈቃደኛ', 'en': 'Volunteer'},
    'regular': {'am': 'መደበኛ', 'en': 'Regular'},
    'temporary': {'am': 'ጊዜያዊ', 'en': 'Temporary'},
    'contract': {'am': 'ውል', 'en': 'Contract'},
    
    # Position Templates
    'position_templates': {'am': 'የሥራ መደብ ቴምፕሌቶች', 'en': 'Position Templates'},
    'template_library': {'am': 'የቴምፕሌት ቤተ-መጻሕፍት', 'en': 'Template Library'},
    'create_from_template': {'am': 'ከቴምፕሌት ፍጠር', 'en': 'Create from Template'},
    'bulk_creation': {'am': 'በብዛት መፍጠሪያ', 'en': 'Bulk Creation'},
    'clone_position': {'am': 'ሥራውን ገልብጥ', 'en': 'Clone Position'},
    'manual_creation': {'am': 'በእጅ መፍጠሪያ', 'en': 'Manual Creation'},
    'template_usage': {'am': 'የቴምፕሌት አጠቃቀም', 'en': 'Template Usage'},
    'available_templates': {'am': 'ያሉ ቴምፕሌቶች', 'en': 'Available Templates'},
    
    # Department Related
    'department_name': {'am': 'የመምሪያ ስም', 'en': 'Department Name'},
    'department_code': {'am': 'የመምሪያ ኮድ', 'en': 'Department Code'},
    'parent_department': {'am': 'ወላጅ መምሪያ', 'en': 'Parent Department'},
    'department_head': {'am': 'የመምሪያ ኃላፊ', 'en': 'Department Head'},
    'department_head_history': {'am': 'የመምሪያ ኃላፊ ታሪክ', 'en': 'Department Head History'},
    'appointment_reason': {'am': 'የምደባ ምክንያት', 'en': 'Appointment Reason'},
    'termination_reason': {'am': 'የማብቃት ምክንያት', 'en': 'Termination Reason'},
    'leadership_start': {'am': 'የአመራር መጀመሪያ', 'en': 'Leadership Start'},
    'leadership_end': {'am': 'የአመራር ማብቃት', 'en': 'Leadership End'},
    
    # Member Career History
    'career_history': {'am': 'የሥራ ታሪክ', 'en': 'Career History'},
    'member_career_history': {'am': 'የአባል የሥራ ታሪክ', 'en': 'Member Career History'},
    'current_positions': {'am': 'የአሁኑ ሥራዎች', 'en': 'Current Positions'},
    'position_history': {'am': 'የሥራ ታሪክ', 'en': 'Position History'},
    'career_timeline': {'am': 'የሥራ የጊዜ መስመር', 'en': 'Career Timeline'},
    'total_positions_held': {'am': 'የተያዙ አጠቃላይ ሥራዎች', 'en': 'Total Positions Held'},
    'leadership_roles': {'am': 'የአመራር ሚናዎች', 'en': 'Leadership Roles'},
    'days_of_service': {'am': 'የአገልግሎት ቀናት', 'en': 'Days of Service'},
    'appointment_type': {'am': 'የምደባ አይነት', 'en': 'Appointment Type'},
    'elected': {'am': 'የተመረጠ', 'en': 'Elected'},
    'appointed': {'am': 'የተሾመ', 'en': 'Appointed'},
    
    # Member Accounts
    'member_accounts': {'am': 'የአባላት መለያዎች', 'en': 'Member Accounts'},
    'portal_accounts': {'am': 'የፖርታል መለያዎች', 'en': 'Portal Accounts'},
    'mobile_accounts': {'am': 'የሞባይል መለያዎች', 'en': 'Mobile Accounts'},
    'account_management': {'am': 'የመለያ አስተዳደር', 'en': 'Account Management'},
    'username': {'am': 'የተጠቃሚ ስም', 'en': 'Username'},
    'password': {'am': 'የይለፍ ቃል', 'en': 'Password'},
    'account_status': {'am': 'የመለያ ሁኔታ', 'en': 'Account Status'},
    'verified': {'am': 'ተረጋግጧል', 'en': 'Verified'},
    'not_verified': {'am': 'አልተረጋገጠም', 'en': 'Not Verified'},
    'last_login': {'am': 'የመጨረሻ መግቢያ', 'en': 'Last Login'},
    'login_count': {'am': 'የመግቢያ ብዛት', 'en': 'Login Count'},
    'login_history': {'am': 'የመግቢያ ታሪክ', 'en': 'Login History'},
    'reset_password': {'am': 'የይለፍ ቃል ዳግም አስጀምር', 'en': 'Reset Password'},
    'change_password': {'am': 'የይለፍ ቃል ቀይር', 'en': 'Change Password'},
    'generate_accounts': {'am': 'መለያዎችን ፍጠር', 'en': 'Generate Accounts'},
    'bulk_generate': {'am': 'በብዛት መለያ መፍጠሪያ', 'en': 'Bulk Generate'},
    'create_account': {'am': 'መለያ ፍጠር', 'en': 'Create Account'},
    'account_exists': {'am': 'መለያ አለ', 'en': 'Account Already Exists'},
    'members_without_accounts': {'am': 'መለያ የሌላቸው አባላት', 'en': 'Members Without Accounts'},
    'total_accounts': {'am': 'አጠቃላይ መለያዎች', 'en': 'Total Accounts'},
    'active_accounts': {'am': 'ንቁ መለያዎች', 'en': 'Active Accounts'},
    'verified_accounts': {'am': 'የተረጋገጡ መለያዎች', 'en': 'Verified Accounts'},
    'accounts_with_login': {'am': 'ተገብተው የነበሩ መለያዎች', 'en': 'Accounts with Login'},
    'suspended': {'am': 'ታግዷል', 'en': 'Suspended'},
    'inactive': {'am': 'ንቁ ያልሆነ', 'en': 'Inactive'},
    
    # Login History
    'login_time': {'am': 'የመግቢያ ሰዓት', 'en': 'Login Time'},
    'logout_time': {'am': 'የመውጫ ሰዓት', 'en': 'Logout Time'},
    'ip_address': {'am': 'የአይፒ አድራሻ', 'en': 'IP Address'},
    'device_info': {'am': 'የመሳሪያ መረጃ', 'en': 'Device Information'},
    'platform': {'am': 'መድረክ', 'en': 'Platform'},
    'app_version': {'am': 'የመተግበሪያ ስሪት', 'en': 'App Version'},
    'session_duration': {'am': 'የክፍለ-ጊዜ ርዝመት', 'en': 'Session Duration'},
    'login_status': {'am': 'የመግቢያ ሁኔታ', 'en': 'Login Status'},
    'success': {'am': 'ተሳክቷል', 'en': 'Success'},
    'failed': {'am': 'አልተሳካም', 'en': 'Failed'},
    'locked': {'am': 'ተቆልፏል', 'en': 'Locked'},
    'failure_reason': {'am': 'የውድቀት ምክንያት', 'en': 'Failure Reason'},
    'successful_logins': {'am': 'የተሳኩ መግቢያዎች', 'en': 'Successful Logins'},
    'failed_attempts': {'am': 'ያልተሳኩ ሙከራዎች', 'en': 'Failed Attempts'},
    'avg_session': {'am': 'አማካይ ክፍለ-ጊዜ', 'en': 'Average Session'},
    
    # Mobile API Related
    'mobile_app': {'am': 'የሞባይል መተግበሪያ', 'en': 'Mobile App'},
    'api_access': {'am': 'የኤፒአይ መዳረሻ', 'en': 'API Access'},
    'authentication': {'am': 'ማረጋገጫ', 'en': 'Authentication'},
    'token': {'am': 'ቶከን', 'en': 'Token'},
    'mobile_platform': {'am': 'የሞባይል መድረክ', 'en': 'Mobile Platform'},
    'ios': {'am': 'አይኦኤስ', 'en': 'iOS'},
    'android': {'am': 'አንድሮይድ', 'en': 'Android'},
    'web': {'am': 'ዌብ', 'en': 'Web'},
    
    # Statistics & Reports
    'total_logins': {'am': 'አጠቃላይ መግቢያዎች', 'en': 'Total Logins'},
    'recent_activity': {'am': 'የቅርብ እንቅስቃሴ', 'en': 'Recent Activity'},
    'login_activity': {'am': 'የመግቢያ እንቅስቃሴ', 'en': 'Login Activity'},
    'career_statistics': {'am': 'የሥራ ስታትስቲክስ', 'en': 'Career Statistics'},
    
    # Common Actions
    'add': {'am': 'አክል', 'en': 'Add'},
    'edit': {'am': 'አስተካክል', 'en': 'Edit'},
    'delete': {'am': 'ሰርዝ', 'en': 'Delete'},
    'save': {'am': 'አስቀምጥ', 'en': 'Save'},
    'cancel': {'am': 'ሰርዝ', 'en': 'Cancel'},
    'search': {'am': 'ፈልግ', 'en': 'Search'},
    'filter': {'am': 'አጣራ', 'en': 'Filter'},
    'export': {'am': 'ወደ ውጪ ላክ', 'en': 'Export'},
    'print': {'am': 'አትም', 'en': 'Print'},
    'download': {'am': 'አውርድ', 'en': 'Download'},
    'upload': {'am': 'ጫን', 'en': 'Upload'},
    'submit': {'am': 'ላክ', 'en': 'Submit'},
    'back': {'am': 'ተመለስ', 'en': 'Back'},
    'next': {'am': 'ቀጣይ', 'en': 'Next'},
    'previous': {'am': 'ቀዳሚ', 'en': 'Previous'},
    'create': {'am': 'ፍጠር', 'en': 'Create'},
    'update': {'am': 'አዘምን', 'en': 'Update'},
    'view': {'am': 'ተመልከት', 'en': 'View'},
    'approve': {'am': 'አጽድቅ', 'en': 'Approve'},
    
    # Common Labels
    'name': {'am': 'ስም', 'en': 'Name'},
    'full_name': {'am': 'ሙሉ ስም', 'en': 'Full Name'},
    'phone': {'am': 'ስልክ', 'en': 'Phone'},
    'email': {'am': 'ኢሜይል', 'en': 'Email'},
    'address': {'am': 'አድራሻ', 'en': 'Address'},
    'date': {'am': 'ቀን', 'en': 'Date'},
    'status': {'am': 'ሁኔታ', 'en': 'Status'},
    'description': {'am': 'መግለጫ', 'en': 'Description'},
    'section': {'am': 'ክፍል', 'en': 'Section'},
    'gender': {'am': 'ፆታ', 'en': 'Gender'},
    'age': {'am': 'ዕድሜ', 'en': 'Age'},
    'total': {'am': 'ድምር', 'en': 'Total'},
    'count': {'am': 'ብዛት', 'en': 'Count'},
    'actions': {'am': 'ተግባራት', 'en': 'Actions'},
    
    # Sections
    'children_section': {'am': 'የሕፃናት ክፍል', 'en': 'Children Section'},
    'youth_section': {'am': 'ወጣት ክፍል', 'en': 'Youth Section'},
    'middle_section': {'am': 'ማህከላዊያን ክፍል', 'en': 'Middle-aged Section'},
    'parent_section': {'am': 'ወላጅ ክፍል', 'en': 'Parent Section'},
    
    # Gender
    'male': {'am': 'ወንድ', 'en': 'Male'},
    'female': {'am': 'ሴት', 'en': 'Female'},
    
    # Marital Status
    'single_male': {'am': 'ያላገባ', 'en': 'Single (Male)'},
    'single_female': {'am': 'ያላገባች', 'en': 'Single (Female)'},
    'married': {'am': 'ያገባ', 'en': 'Married'},
    'divorced_male': {'am': 'የፈታ', 'en': 'Divorced (Male)'},
    'divorced_female': {'am': 'የፈታች', 'en': 'Divorced (Female)'},
    
    # Work Status
    'employed': {'am': 'በሥራ ላይ', 'en': 'Employed'},
    'unemployed': {'am': 'ስራ የለኝም', 'en': 'Unemployed'},
    'job_seeking': {'am': 'በመፈለግ ላይ', 'en': 'Job Seeking'},
    'student': {'am': 'ተማሪ', 'en': 'Student'},
    
    # Attendance
    'present': {'am': 'ተገኝቷል', 'en': 'Present'},
    'absent': {'am': 'አልተገኘም', 'en': 'Absent'},
    'excuse': {'am': 'ሰበብ', 'en': 'Excused'},
    
    # Statistics
    'total_members': {'am': 'ጠቅላላ አባላት', 'en': 'Total Members'},
    'male_count': {'am': 'ወንዶች', 'en': 'Males'},
    'female_count': {'am': 'ሴቶች', 'en': 'Females'},
    'active_members': {'am': 'ንቁ አባላት', 'en': 'Active Members'},
    
    # Messages
    'success': {'am': 'ተሳክቷል!', 'en': 'Success!'},
    'error': {'am': 'ስህተት!', 'en': 'Error!'},
    'warning': {'am': 'ማስጠንቀቂያ!', 'en': 'Warning!'},
    'info': {'am': 'መረጃ', 'en': 'Information'},
    'confirm_delete': {'am': 'መሰረዝ ይፈልጋሉ?', 'en': 'Are you sure you want to delete?'},
    'saved_successfully': {'am': 'በተሳካ ሁኔታ ተቀምጧል', 'en': 'Saved successfully'},
    'deleted_successfully': {'am': 'በተሳካ ሁኔታ ተሰርዟል', 'en': 'Deleted successfully'},
    'updated_successfully': {'am': 'በተሳካ ሁኔታ ተዘምኗል', 'en': 'Updated successfully'},
    
    # Forms
    'required_field': {'am': 'የሚያስፈልግ መረጃ', 'en': 'Required Field'},
    'optional_field': {'am': 'አማራጭ', 'en': 'Optional'},
    'select_option': {'am': 'ይምረጡ', 'en': 'Select an option'},
    'enter_value': {'am': 'ያስገቡ', 'en': 'Enter value'},
    
    # User Management
    'username': {'am': 'የተጠቃሚ ስም', 'en': 'Username'},
    'password': {'am': 'የይለፍ ቃል', 'en': 'Password'},
    'role': {'am': 'ሚና', 'en': 'Role'},
    'permissions': {'am': 'ፈቃዶች', 'en': 'Permissions'},
    'active': {'am': 'ንቁ', 'en': 'Active'},
    'inactive': {'am': 'ቦዘኛ', 'en': 'Inactive'},
    'last_login': {'am': 'የመጨረሻ መግቢያ', 'en': 'Last Login'},
    
    # Library
    'book_title': {'am': 'የመፅሀፍ ርዕስ', 'en': 'Book Title'},
    'author': {'am': 'ደራሲ', 'en': 'Author'},
    'isbn': {'am': 'ISBN', 'en': 'ISBN'},
    'category': {'am': 'ምድብ', 'en': 'Category'},
    'available': {'am': 'ዝግጁ', 'en': 'Available'},
    'borrowed': {'am': 'ተበደረ', 'en': 'Borrowed'},
    'borrow_date': {'am': 'የመበደር ቀን', 'en': 'Borrow Date'},
    'return_date': {'am': 'የመመለስ ቀን', 'en': 'Return Date'},
    
    # MEWACO
    'contribution': {'am': 'መዋጮ', 'en': 'Contribution'},
    'amount': {'am': 'መጠን', 'en': 'Amount'},
    'paid': {'am': 'ተከፍሏል', 'en': 'Paid'},
    'unpaid': {'am': 'አልተከፈለም', 'en': 'Unpaid'},
    'partial': {'am': 'በከፊል', 'en': 'Partial'},
    'month': {'am': 'ወር', 'en': 'Month'},
    'year': {'am': 'ዓመት', 'en': 'Year'},
    
    # Inventory
    'inventory': {'am': 'የእቃ አስተዳደር', 'en': 'Inventory'},
    'inventory_management': {'am': 'የእቃ አስተዳደር', 'en': 'Inventory Management'},
    'inventory_items': {'am': 'የእቃ መዝገብ', 'en': 'Inventory Items'},
    'inventory_transactions': {'am': 'የእቃ እንቅስቃሴ', 'en': 'Inventory Transactions'},
    'stock_report': {'am': 'የእቃ ሪፖርት', 'en': 'Stock Report'},
    'movement_report': {'am': 'የእንቅስቃሴ ሪፖርት', 'en': 'Movement Report'},
    'item_name': {'am': 'የእቃ ስም', 'en': 'Item Name'},
    'quantity': {'am': 'መጠን', 'en': 'Quantity'},
    'unit': {'am': 'መለኪያ', 'en': 'Unit'},
    'location': {'am': 'ቦታ', 'en': 'Location'},
    'supplier': {'am': 'አቅራቢ', 'en': 'Supplier'},
    'purchase_date': {'am': 'የግዢ ቀን', 'en': 'Purchase Date'},
    'unit_price': {'am': 'የአንድ ዋጋ', 'en': 'Unit Price'},
    'total_value': {'am': 'ጠቅላላ ዋጋ', 'en': 'Total Value'},
    'min_stock': {'am': 'ዝቅተኛ መጠን', 'en': 'Minimum Stock'},
    'low_stock': {'am': 'ዝቅተኛ እቃ', 'en': 'Low Stock'},
    'out_of_stock': {'am': 'ያለቀ እቃ', 'en': 'Out of Stock'},
    'in_stock': {'am': 'በእቃ ላይ', 'en': 'In Stock'},
    'incoming': {'am': 'ገቢ', 'en': 'Incoming'},
    'outgoing': {'am': 'ወጪ', 'en': 'Outgoing'},
    'adjustment': {'am': 'ማስተካከያ', 'en': 'Adjustment'},
    'transaction_type': {'am': 'የእንቅስቃሴ አይነት', 'en': 'Transaction Type'},
    'reference_number': {'am': 'ማመሳከሪያ ቁጥር', 'en': 'Reference Number'},
    'responsible_user': {'am': 'ኃላፊነት ያለው', 'en': 'Responsible User'},
    'recipient': {'am': 'ተቀባይ', 'en': 'Recipient'},
    'purpose': {'am': 'ዓላማ', 'en': 'Purpose'},
    
    # Common Phrases
    'welcome': {'am': 'እንኳን ደህና መጡ', 'en': 'Welcome'},
    'logout': {'am': 'ውጣ', 'en': 'Logout'},
    'profile': {'am': 'መገለጫ', 'en': 'Profile'},
    'settings': {'am': 'ቅንብሮች', 'en': 'Settings'},
    'help': {'am': 'እገዛ', 'en': 'Help'},
    'language': {'am': 'ቋንቋ', 'en': 'Language'},
    'select_language': {'am': 'ቋንቋ ይምረጡ', 'en': 'Select Language'},
    
    # Pagination
    'showing': {'am': 'በማሳየት ላይ', 'en': 'Showing'},
    'of': {'am': 'ከ', 'en': 'of'},
    'entries': {'am': 'ግቤቶች', 'en': 'entries'},
    'no_data': {'am': 'ምንም መረጃ የለም', 'en': 'No data available'},
    
    # Time
    'today': {'am': 'ዛሬ', 'en': 'Today'},
    'yesterday': {'am': 'ትላንት', 'en': 'Yesterday'},
    'this_week': {'am': 'በዚህ ሳምንት', 'en': 'This Week'},
    'this_month': {'am': 'በዚህ ወር', 'en': 'This Month'},
    'this_year': {'am': 'በዚህ ዓመት', 'en': 'This Year'},
    
    # File Upload
    'select_file': {'am': 'ፋይል ይምረጡ', 'en': 'Select File'},
    'drag_drop': {'am': 'ፋይል ይጎትቱ እና ይጣሉ', 'en': 'Drag & Drop File'},
    'upload_file': {'am': 'ፋይል ያስገቡ', 'en': 'Upload File'},
    'download_template': {'am': 'ቅጽ አውርድ', 'en': 'Download Template'},
    'file_selected': {'am': 'ፋይል ተመርጧል', 'en': 'File Selected'},
    
    # Results
    'success_count': {'am': 'የተሳካ', 'en': 'Successful'},
    'error_count': {'am': 'ስህተት', 'en': 'Errors'},
    'duplicate_count': {'am': 'ድግግሞሽ', 'en': 'Duplicates'},
    'total_rows': {'am': 'ጠቅላላ ረድፎች', 'en': 'Total Rows'},
    
    # Table Headers
    'row_number': {'am': 'ረድፍ ቁጥር', 'en': 'Row Number'},
    'details': {'am': 'ዝርዝር', 'en': 'Details'},
    
    # Page Titles
    'member_management_title': {'am': 'የአባላት አስተዳደር ስርዓት', 'en': 'Member Management System'},
    'attendance_title': {'am': 'የተገኝነት አስተዳደር', 'en': 'Attendance Management'},
    'library_title': {'am': 'የቤተ መፃህፍት አስተዳደር', 'en': 'Library Management'},
    'contribution_title': {'am': 'የመዋጮ አስተዳደር', 'en': 'Contribution Management'},
    
    # Instructions
    'instructions': {'am': 'መመሪያዎች', 'en': 'Instructions'},
    'how_to_use': {'am': 'እንዴት እንደሚጠቀሙ', 'en': 'How to Use'},
    'step': {'am': 'ደረጃ', 'en': 'Step'},
    
    # Months
    'january': {'am': 'ጃንዋሪ', 'en': 'January'},
    'february': {'am': 'ፌብሩወሪ', 'en': 'February'},
    'march': {'am': 'ማርች', 'en': 'March'},
    'april': {'am': 'ኤፕሪል', 'en': 'April'},
    'may': {'am': 'ሜይ', 'en': 'May'},
    'june': {'am': 'ጁን', 'en': 'June'},
    'july': {'am': 'ጁላይ', 'en': 'July'},
    'august': {'am': 'ኦገስት', 'en': 'August'},
    'september': {'am': 'ሴፕቴምበር', 'en': 'September'},
    'october': {'am': 'ኦክቶበር', 'en': 'October'},
    'november': {'am': 'ኖቬምበር', 'en': 'November'},
    'december': {'am': 'ዲሴምበር', 'en': 'December'},
}

def get_text(key, lang='am'):
    """
    Get translated text for a given key and language.
    
    Args:
        key: Translation key
        lang: Language code ('am' for Amharic, 'en' for English)
    
    Returns:
        Translated text or the key itself if not found
    """
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get('am', key))
    return key

def translate(key, lang='am'):
    """Alias for get_text"""
    return get_text(key, lang)

