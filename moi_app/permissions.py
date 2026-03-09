# File: custom_asset_permissions.py

import frappe

def get_permission_query_conditions_for_asset(user):
    """Restrict Head of Department to their department only"""
    if not user:
        user = frappe.session.user
    
    # Skip for System Manager/Administrator
    if any(role in frappe.get_roles(user) for role in ["System Manager","Asset Manager", "Administrator"]):
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

def get_permission_query_conditions_for_employee(user):
    """Restrict Head of Department to employees in their department only"""
    if not user:
        user = frappe.session.user
    
    # Skip for System Manager/Administrator/HR Manager
    if any(role in frappe.get_roles(user) for role in ["System Manager", "HR Manager", "Administrator"]):
        return ""
    
    # Get user's department
    user_department = frappe.db.get_value("Employee", {"user_id": user}, "department")
    
    if not user_department:
        # If user has no department assigned, show nothing
        return "(`tabEmployee`.department IS NULL AND 1=0)"
    
    # For Head of Department - only employees in their department
    if "Head of Department" in frappe.get_roles(user):
        # Get child departments if hierarchical structure exists
        child_departments = frappe.db.get_list(
            "Department",
            filters={"parent_department": user_department},
            pluck="name"
        )
        
        if child_departments:
            departments_list = ", ".join([f"'{dept}'" for dept in child_departments])
            departments_list += f", '{user_department}'"  # Include parent department
            return f"""(`tabEmployee`.department IN ({departments_list}))"""
        else:
            return f"""(`tabEmployee`.department = '{user_department}')"""
    
    return ""

import frappe

def employee_query_condition(user=None):
    """
    Restrict Employee visibility:
    - HR Manager/HR User: See all employees
    - Head of Department: See their department + subordinates
    - Regular users: See only themselves
    """
    if not user:
        user = frappe.session.user
    
    # Skip restrictions for privileged roles
    privileged_roles = {"HR Manager", "HR User","Asset manager", "System Manager", "Administrator"}
    if set(frappe.get_roles(user)) & privileged_roles:
        return ""
    
    # Get user's employee record
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return "1=0"  # No employee record = no visibility
    
    # Head of Department: see department + subordinates
    if "Head of Department" in frappe.get_roles(user):
        department = frappe.db.get_value("Employee", employee, "department")
        if not department:
            return f"`tabEmployee`.name = '{employee}'"
        
        # Get all employees in department + sub-departments
        departments = [department]
        child_departments = frappe.db.get_list(
            "Department",
            filters={"parent_department": department},
            pluck="name"
        )
        departments.extend(child_departments)
        
        dept_list = ", ".join(f"'{d}'" for d in departments)
        return f"`tabEmployee`.department IN ({dept_list})"
    
    # Regular user: see only themselves
    return f"`tabEmployee`.name = '{employee}'"


def material_request_query_condition(user=None):
    """
    Restrict Material Request visibility:
    - Approvers (Finance/Asset/Purchase Manager): See ALL requests
    - Regular users: See only their own requests OR requests where applicant reports to them
    """
    if not user:
        user = frappe.session.user
    
    # Approvers need to see ALL requests for workflow approval
    approver_roles = {
        "Finance Manager", 
        "Asset Manager", 
        "Purchase Manager",
        "System Manager", 
        "Administrator"
    }
    if set(frappe.get_roles(user)) & approver_roles:
        return ""  # No restriction - see all Material Requests
    
    # Regular users: see own requests + requests for their subordinates
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return f"`tabMaterial Request`.owner = '{user}'"
    
    # Get subordinates
    subordinates = frappe.db.get_list(
        "Employee",
        filters={"reports_to": employee},
        pluck="name"
    )
    subordinates.append(employee)  # Include self
    
    emp_list = ", ".join(f"'{e}'" for e in subordinates)
    return f"(`tabMaterial Request`.applicant IN ({emp_list}) OR `tabMaterial Request`.owner = '{user}')"