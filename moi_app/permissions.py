# File: custom_asset_permissions.py

import frappe

def get_permission_query_conditions_for_asset(user):
    """Restrict Head of Department to their department only"""
    frappe.logger().info(f"🔍 [ASSET PERMISSIONS] Function called for user: {user}")
    if not user:
        user = frappe.session.user
    
    # Skip for System Manager/Administrator
    if "System Manager" in frappe.get_roles(user) or "Administrator" in frappe.get_roles(user):
        return ""
    
    # Get user's department
    user_department = frappe.db.get_value("Employee", {"user_id": user}, "department")
    
    if not user_department:
        # If user has no department assigned, show nothing
        return "(`tabAsset`.department IS NULL AND 1=0)"
    
    # For Head of Department - only their department
    if "Head of Department" in frappe.get_roles(user):
        # Get child departments if hierarchical structure exists
        child_departments = ""
        
        if child_departments:
            departments_list = ", ".join([f"'{dept}'" for dept in child_departments])
            return f"""(`tabAsset`.department IN ({departments_list}))"""
        else:
            return f"""(`tabAsset`.department = '{user_department}')"""
    
    return ""

