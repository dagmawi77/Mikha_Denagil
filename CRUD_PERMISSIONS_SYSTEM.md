# Granular CRUD & Approval Permissions System

## ✅ Complete Implementation - Enterprise-Grade Access Control

### 🎯 Overview

The system now implements **granular, action-level permissions** for every endpoint. Instead of simple "access or no access," administrators can now control exactly what users can do on each feature:

- ✅ **Create** - Add new records
- ✅ **Read** - View/access data  
- ✅ **Update** - Edit existing records
- ✅ **Delete** - Remove records
- ✅ **Approve** - Approve requests, changes, or workflows
- ✅ **Export** - Download/export data (PDF, Excel, CSV)

---

## 🗄️ Database Schema Changes

### **Enhanced `role_routes` Table**

```sql
CREATE TABLE role_routes (
    role_id INT NOT NULL,
    route_id INT NOT NULL,
    can_create TINYINT(1) DEFAULT 0,      -- Create permission
    can_read TINYINT(1) DEFAULT 1,        -- Read permission (default)
    can_update TINYINT(1) DEFAULT 0,      -- Update permission
    can_delete TINYINT(1) DEFAULT 0,      -- Delete permission
    can_approve TINYINT(1) DEFAULT 0,     -- Approval permission
    can_export TINYINT(1) DEFAULT 0,      -- Export permission
    PRIMARY KEY (role_id, route_id),
    FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE,
    FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE
);
```

### **Migration**
The system automatically adds these columns to existing `role_routes` tables on startup with safe migration logic.

---

## 🔧 Backend Implementation

### **1. Database Layer (`database.py`)**

#### **Auto-Migration Code**
```python
# Add CRUD permission columns to existing role_routes table
crud_columns = [
    ('can_create', 'TINYINT(1) DEFAULT 0'),
    ('can_read', 'TINYINT(1) DEFAULT 1'),
    ('can_update', 'TINYINT(1) DEFAULT 0'),
    ('can_delete', 'TINYINT(1) DEFAULT 0'),
    ('can_approve', 'TINYINT(1) DEFAULT 0'),
    ('can_export', 'TINYINT(1) DEFAULT 0')
]

for column_name, column_def in crud_columns:
    # Check if column exists
    # Add if missing
    # Safe for existing installations
```

**Features:**
- Checks existing schema
- Only adds missing columns
- Preserves existing data
- No disruption to running systems

---

### **2. Authentication Layer (`auth.py`)**

#### **New Functions Added:**

##### **a. `check_permission(endpoint, permission_type)`**
```python
check_permission('manage_members', 'create')  # Returns True/False
check_permission('manage_members', 'delete')  # Returns True/False
```

**Usage:**
- Check if current user has specific permission
- Used in templates and route logic
- Super Admin always returns True

##### **b. `permission_required(endpoint, permission_type)` Decorator**
```python
@permission_required('manage_members', 'create')
def create_member():
    # Only users with 'create' permission can access
    pass

@permission_required('manage_members', 'delete')
def delete_member():
    # Only users with 'delete' permission can access
    pass
```

**Features:**
- Protects routes with specific permissions
- Shows appropriate error messages
- Redirects unauthorized users
- Works with existing login system

##### **c. `get_user_permissions(endpoint)`**
```python
perms = get_user_permissions('manage_members')
# Returns:
# {
#     'can_create': True,
#     'can_read': True,
#     'can_update': False,
#     'can_delete': False,
#     'can_approve': False,
#     'can_export': True
# }
```

**Usage:**
- Get all permissions for an endpoint at once
- Pass to templates for UI control
- Conditionally show/hide buttons

---

### **3. Route Layer (`app_modular.py`)**

#### **Updated `manage_role_routes` Route**

**Before:**
```python
# Simple checkbox - route enabled or not
selected_routes = request.form.getlist('routes')
for route_id in selected_routes:
    cursor.execute("INSERT INTO role_routes (role_id, route_id) VALUES (%s, %s)")
```

**After:**
```python
# Granular CRUD permissions per route
selected_routes = request.form.getlist('routes')
for route_id in selected_routes:
    can_create = 1 if f'can_create_{route_id}' in request.form else 0
    can_read = 1 if f'can_read_{route_id}' in request.form else 0
    can_update = 1 if f'can_update_{route_id}' in request.form else 0
    can_delete = 1 if f'can_delete_{route_id}' in request.form else 0
    can_approve = 1 if f'can_approve_{route_id}' in request.form else 0
    can_export = 1 if f'can_export_{route_id}' in request.form else 0
    
    cursor.execute("""
        INSERT INTO role_routes 
        (role_id, route_id, can_create, can_read, can_update, can_delete, can_approve, can_export)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """)
```

**Features:**
- Saves individual CRUD flags per route
- Retrieves existing permissions for display
- Passes permission data to template

---

## 🎨 Frontend Implementation

### **Enhanced `manage_role_routes.html`**

#### **Key UI Features:**

##### **1. Info Banner**
- Explains CRUD permissions
- Color-coded legend:
  - 🟢 **Create** - Green
  - 🔵 **Read** - Blue
  - 🟡 **Update** - Yellow
  - 🔴 **Delete** - Red
  - 🟣 **Approve** - Purple
  - 🔷 **Export** - Cyan

##### **2. Route Cards with CRUD Grid**
```html
<div class="route-card">
    <div class="route-header">
        <input type="checkbox" name="routes" value="123">
        <label>Manage Members</label>
    </div>
    
    <div class="crud-permissions">
        <!-- 6 permission checkboxes in 3x2 grid -->
        <div class="permission-item">
            <input type="checkbox" name="can_create_123">
            <label>Create</label>
        </div>
        <!-- ... more permissions -->
    </div>
</div>
```

##### **3. Interactive Behavior**

**Auto-enable Route:**
```javascript
// When user checks any CRUD permission,
// automatically enable the route checkbox
function togglePermission(item, event) {
    const checkbox = item.querySelector('input[type="checkbox"]');
    checkbox.checked = !checkbox.checked;
    
    if (checkbox.checked) {
        // Auto-enable main route
        const mainCheckbox = card.querySelector('.route-main-checkbox');
        mainCheckbox.checked = true;
    }
}
```

**Auto-enable Read:**
```javascript
// When route is enabled, auto-check "Read" permission
function toggleRouteCard(checkbox) {
    if (checkbox.checked) {
        const readCheckbox = card.querySelector('[id^="read_"]');
        readCheckbox.checked = true;  // Auto-enable Read
    }
}
```

**Disable All:**
```javascript
// When route is disabled, uncheck all permissions
if (!checkbox.checked) {
    card.querySelectorAll('.permission-item input').forEach(cb => {
        cb.checked = false;
    });
}
```

##### **4. Visual Feedback**
- **Inactive Permission**: Gray background, no border
- **Active Permission**: Light green tint, green border
- **Hover**: Gray background highlight
- **Icon Colors**: Match permission type

---

## 📋 Usage Examples

### **Example 1: Librarian Role**
**Requirements:** Can view library, add books, but cannot delete books or approve loans

**Configuration:**
```
Endpoint: manage_books
✓ Create (add new books)
✓ Read (view books)
✓ Update (edit book details)
✗ Delete (cannot remove books)
✗ Approve (no approval workflow)
✓ Export (download book list)

Endpoint: borrow_management
✗ Create (cannot initiate loans)
✓ Read (view borrowing records)
✗ Update (cannot modify records)
✗ Delete (cannot delete records)
✗ Approve (cannot approve loans)
✗ Export (cannot export data)
```

---

### **Example 2: Finance Manager Role**
**Requirements:** Full access to MEWACO, can approve contributions

**Configuration:**
```
Endpoint: mewaco_contributions
✓ Create (record contributions)
✓ Read (view contributions)
✓ Update (edit contribution records)
✗ Delete (cannot delete for audit)
✓ Approve (approve pending contributions)
✓ Export (export reports)

Endpoint: contribution_report_monthly
✗ Create (reports are generated)
✓ Read (view reports)
✗ Update (reports are read-only)
✗ Delete (cannot delete reports)
✗ Approve (no approval needed)
✓ Export (download reports)
```

---

### **Example 3: Section Leader Role**
**Requirements:** Manage members in their section only, no delete rights

**Configuration:**
```
Endpoint: manage_members
✓ Create (add members to section)
✓ Read (view member list)
✓ Update (edit member details)
✗ Delete (cannot remove members)
✗ Approve (no approval workflow)
✗ Export (cannot export data)

Endpoint: attendance
✓ Create (mark attendance)
✓ Read (view attendance)
✓ Update (correct attendance errors)
✗ Delete (cannot delete attendance)
✗ Approve (no approval needed)
✗ Export (cannot export)
```

---

## 🔐 Security Implementation

### **1. Route Protection**

#### **Basic Route Protection (Endpoint Level)**
```python
@app.route('/manage_members')
@login_required
@role_required('Manager', 'Admin')
def manage_members():
    # User can access this page
    pass
```

#### **Action-Level Protection (CRUD Level)**
```python
@app.route('/manage_members', methods=['POST'])
@login_required
@permission_required('manage_members', 'create')
def create_member():
    # Only if user has 'create' permission
    pass

@app.route('/delete_member/<int:id>', methods=['POST'])
@login_required
@permission_required('manage_members', 'delete')
def delete_member(id):
    # Only if user has 'delete' permission
    pass
```

---

### **2. Template-Level Control**

#### **Conditional Button Display**
```python
# In route
perms = get_user_permissions('manage_members')
return render_template('manage_members.html', permissions=perms)
```

```html
<!-- In template -->
{% if permissions.can_create %}
    <button class="btn btn-create">Add Member</button>
{% endif %}

{% if permissions.can_update %}
    <a href="{{ url_for('edit_member', id=member.id) }}" class="btn btn-edit">Edit</a>
{% endif %}

{% if permissions.can_delete %}
    <button class="btn btn-delete">Delete</button>
{% endif %}

{% if permissions.can_export %}
    <button class="btn btn-export">Export</button>
{% endif %}

{% if permissions.can_approve %}
    <button class="btn btn-approve">Approve</button>
{% endif %}
```

---

### **3. Dynamic UI**

#### **Hide/Show Based on Permissions**
```javascript
// Check permission in JavaScript (passed from server)
const permissions = {{ permissions|tojson }};

if (!permissions.can_delete) {
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.style.display = 'none';
    });
}

if (!permissions.can_create) {
    document.getElementById('createForm').style.display = 'none';
}
```

---

## 🎯 Permission Matrix Example

| Role | Endpoint | Create | Read | Update | Delete | Approve | Export |
|------|----------|--------|------|--------|--------|---------|--------|
| **Super Admin** | All | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Manager** | manage_members | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| **Librarian** | manage_books | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| **Librarian** | borrow_management | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Finance** | mewaco_contributions | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| **Section Leader** | attendance | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Treasurer** | mewaco_types | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Viewer** | All reports | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |

---

## 📊 Benefits

### **1. Enhanced Security**
- Fine-grained control over user actions
- Prevent unauthorized data modifications
- Audit-friendly (can track who has what permissions)

### **2. Workflow Support**
- Separate approval permissions from edit permissions
- Support for multi-level approval processes
- Export control for sensitive data

### **3. Flexible Role Design**
- Same role can have different permissions per feature
- Easy to customize for organizational needs
- No need to create multiple similar roles

### **4. Better User Experience**
- Users only see what they can do
- Clearer interface (no disabled buttons)
- Less confusion about capabilities

### **5. Compliance**
- Segregation of duties (SOD)
- Principle of least privilege
- Audit trail ready

---

## 🔄 Migration Path

### **For Existing Installations:**

1. **Automatic Column Addition**
   - System detects missing columns
   - Adds them automatically on startup
   - Default values: Read=1, Others=0

2. **Existing Permissions**
   - All existing route assignments get "Read" permission
   - Admins must manually configure other permissions
   - No disruption to current access

3. **Backward Compatible**
   - Old `role_required()` decorator still works
   - New `permission_required()` is optional
   - Gradual migration possible

---

## 🚀 Implementation Checklist

### **Database:**
- [x] Add CRUD columns to role_routes table
- [x] Create migration logic
- [x] Test with existing data

### **Backend:**
- [x] Create `check_permission()` function
- [x] Create `permission_required()` decorator
- [x] Create `get_user_permissions()` function
- [x] Update `manage_role_routes` route
- [x] Update form submission logic

### **Frontend:**
- [x] Redesign route cards with CRUD grid
- [x] Add permission checkboxes (6 per route)
- [x] Implement auto-enable logic
- [x] Add visual feedback
- [x] Create info banner with legend
- [x] Add color-coding

### **Documentation:**
- [x] System overview
- [x] API documentation
- [x] Usage examples
- [x] Migration guide

---

## 📚 API Reference

### **Python Functions**

#### **`check_permission(endpoint, permission_type='read')`**
```python
Args:
    endpoint (str): Route endpoint name (e.g., 'manage_members')
    permission_type (str): 'create', 'read', 'update', 'delete', 'approve', 'export'

Returns:
    bool: True if user has permission, False otherwise

Example:
    if check_permission('manage_members', 'delete'):
        # User can delete members
        pass
```

#### **`@permission_required(endpoint, permission_type)`**
```python
Decorator to protect routes with specific permissions.

Args:
    endpoint (str): Route endpoint name
    permission_type (str): Permission type required

Example:
    @permission_required('manage_members', 'create')
    def create_member():
        pass
```

#### **`get_user_permissions(endpoint)`**
```python
Args:
    endpoint (str): Route endpoint name

Returns:
    dict: Dictionary with all permission flags
    {
        'can_create': bool,
        'can_read': bool,
        'can_update': bool,
        'can_delete': bool,
        'can_approve': bool,
        'can_export': bool
    }

Example:
    perms = get_user_permissions('manage_members')
    if perms['can_create']:
        # Show create button
        pass
```

---

## 🎉 Summary

The system now provides **enterprise-grade, granular access control** with:

✅ **6 Permission Types** per endpoint (CRUD + Approve + Export)  
✅ **Action-Level Security** - Control what users can do, not just what they can see  
✅ **Visual Permission Management** - Intuitive UI with color-coding  
✅ **Automatic Migration** - Safe upgrade for existing installations  
✅ **Flexible Configuration** - Mix and match permissions per role/endpoint  
✅ **Audit-Ready** - Track who has what permissions  
✅ **Workflow Support** - Separate approval from modification rights  
✅ **Template Integration** - Easy to use in templates  
✅ **Decorator Support** - Simple route protection  

**This is production-ready, enterprise-level access control!** 🚀

