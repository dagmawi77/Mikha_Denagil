"""
Admin API Blueprints
Provides Flask blueprints for admin, organization, and staff management routes
"""

from flask import Blueprint

# Create admin API blueprint
admin_api = Blueprint('admin_api', __name__, url_prefix='/admin')

# Create organization API blueprint
org_api = Blueprint('org_api', __name__, url_prefix='/org')

# Create staff API blueprint
staff_api = Blueprint('staff_api', __name__, url_prefix='/staff')

# Export blueprints
__all__ = ['admin_api', 'org_api', 'staff_api']

