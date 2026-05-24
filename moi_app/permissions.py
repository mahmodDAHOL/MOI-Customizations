# File: custom_asset_permissions.py

import frappe



def get_permission_query_conditions_for_employee(user):
    """Restrict Head of Department to employees in their department only"""
    if not user:
        user = frappe.session.user
    
    # Skip for System Manager/Administrator/HR Manager
    if any(role in frappe.get_roles(user) for role in ["System Manager", "Administrator","Asset manager"]):
        return ""

    if any(role in frappe.get_roles(user) for role in ["HR Manager","HR User"]):
        return f"""(`tabEmployee`.company = 'Ministry of Information')"""
    
    emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    # return f"""(`tabEmployee`.name = '{emp_id}')"""
    # Get user's department and employee ID
    user_department = frappe.db.get_value("Employee", {"user_id": user}, "department")
    emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    if not user_department:
        # If user has no department assigned, show nothing
        return "(`tabEmployee`.department IS NULL AND 1=0)"
    
    # For Head of Department - only employees in their department
    # if "Head of Department" in frappe.get_roles(user):
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
    
    # # Differentiate between list view and link field
    # if is_link_field_selection():
    #     # For link fields - show employees in same department
    #     return ""
    # else:
    #     # For Employee list view - only their own record
    #     return f"""(`tabEmployee`.name = '{emp_id}')"""
    


def is_link_field_selection():
    """Determine if the query is for a link field selection dialog"""
    # Check request path
    if hasattr(frappe, 'request') and frappe.request:
        path = frappe.request.path or ''
        
        if '/api/method/frappe.desk.search.search_link' in path:
            return True
        if '/api/method/frappe.desk.reportview.get' in path:
            return False
    
    # Check if there's a 'txt' parameter (typical for link fields)
    if hasattr(frappe, 'form_dict') and frappe.form_dict:
        if 'txt' in frappe.form_dict and 'page_len' in frappe.form_dict:
            return True
    
    # Check if called from specific Frappe methods
    import inspect
    stack = inspect.stack()
    for frame in stack:
        if 'get_link_query' in str(frame.code_context):
            return True
        if 'build_match_conditions' in str(frame.code_context):
            # For link fields, build_match_conditions is called
            return True
    
    return False

# def employee_query_condition(user=None):
#     """
#     Restrict Employee visibility:
#     - HR Manager/HR User: See all employees
#     - Head of Department: See their department + subordinates
#     - Regular users: See only themselves
#     """
#     if not user:
#         user = frappe.session.user
    
#     # Skip restrictions for privileged roles
#     privileged_roles = {"HR Manager", "HR User", "System Manager", "Administrator"}
#     if set(frappe.get_roles(user)) & privileged_roles:
#         return ""
    
#     # Get user's employee record
#     employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
#     if not employee:
#         return "1=0"  # No employee record = no visibility
    
#     # Head of Department: see department + subordinates
#     if "Head of Department" in frappe.get_roles(user):
#         department = frappe.db.get_value("Employee", employee, "department")
#         if not department:
#             return f"`tabEmployee`.name = '{employee}'"
        
#         # Get all employees in department + sub-departments
#         departments = [department]
#         child_departments = frappe.db.get_list(
#             "Department",
#             filters={"parent_department": department},
#             pluck="name"
#         )
#         departments.extend(child_departments)
        
#         dept_list = ", ".join(f"'{d}'" for d in departments)
#         return f"`tabEmployee`.department IN ({dept_list})"
    
#     # Regular user: see only themselves
#     return f"`tabEmployee`.name = '{employee}'"


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
        "Finance-Officer", 
        "Purchase Manager",
        "System Manager", 
        "Administrator"
    }
    # all([frappe.db.get_value('Item', i.item_code, 'is_fixed_asset') for i in doc.items])
    if set(frappe.get_roles(user)) & approver_roles:
        return ""  # No restriction - see all Material Requests
    if "Asset manager" in frappe.get_roles(user):
        return f"`tabMaterial Request`.custom_is_all_items_are_assets = '1'"

    if "Shared-Services-Stock" in frappe.get_roles(user):
        return f"`tabMaterial Request`.custom_is_all_items_are_assets = '0'"

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
    return f"(`tabMaterial Request`.custom_applicant IN ({emp_list}) OR `tabMaterial Request`.owner = '{user}')"


def asset_query_condition(user=None):
    """
    Restrict Asset visibility based on user roles:
    - HR Manager/HR User: See NO assets
    - Asset Manager: See all assets
    - Head of Department: See assets of their department + subordinates
    - Regular users: See only assets assigned to themselves
    """
    if not user:
        user = frappe.session.user
    
    # Get user's roles
    user_roles = set(frappe.get_roles(user))

    # Full access for asset managers
    asset_privileged_roles = {"Asset manager", "System Manager", "Administrator"}
    if user_roles & asset_privileged_roles:
        return ""
    
    # Get user's employee record
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return "1=0"
    
    # Head of Department: see assets of their department
    if "Head of Department" in user_roles:
        department = frappe.db.get_value("Employee", employee, "department")
        if not department:
            return f"`tabAsset`.custodian = '{employee}'"
        
        # Get all employees in department + sub-departments
        departments = [department]
        child_departments = frappe.db.get_list(
            "Department",
            filters={"parent_department": department},
            pluck="name"
        )
        departments.extend(child_departments)
        
        # Get all employees in these departments
        employees_in_dept = frappe.db.get_list(
            "Employee",
            filters={"department": ["in", departments]},
            pluck="name"
        )
        
        if not employees_in_dept:
            return "1=0"
        
        emp_list = ", ".join(f"'{emp}'" for emp in employees_in_dept)
        return f"`tabAsset`.custodian IN ({emp_list})"
    
    # Regular user: see only assets where they are custodian
    return f"`tabAsset`.custodian = '{employee}'"


def employee_query_condition(user=None):
    """Show users in same department as current user"""
    if not user:
        user = frappe.session.user
    
    # Skip restrictions for privileged roles
    privileged_roles = {"HR Manager", "HR User","System Manager", "Administrator"}
    if set(frappe.get_roles(user)) & privileged_roles:
        return ""
    
    # Get current user's employee record
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        # If no employee record, only see themselves
        return f"`tabEmployee`.name = '{user}'"
    
    # Get user's department
    department = frappe.db.get_value("Employee", employee, "department")
    if not department:
        # If no department, only see themselves
        return f"`tabEmployee`.name = '{user}'"
    
    # Get all employees in department + sub-departments
    departments = [department]
    child_departments = frappe.db.get_list(
        "Department",
        filters={"parent_department": department},
        pluck="name"
    )
    departments.extend(child_departments)
    
    # Get all users in those departments
    employees_in_dept = frappe.db.get_list(
        "Employee",
        filters={"department": ["in", departments]},
        pluck="user_id",
        ignore_permissions=True  # Important to avoid recursion
    )

    # Remove None values and convert to SQL format
    employee_list = [f"'{e}'" for e in employees_in_dept if e]

    employee_list_str = ", ".join(employee_list)
    return f"`tabEmployee`.name IN ({employee_list_str})"


def vehicle_query_conditions(user):
    """Return conditions to filter Vehicle records based on user role"""
    
    # Check if user has Shared-Services-Vehicles role
    user_roles = frappe.get_roles(user)
    
    if "Shared-Services-Vehicles" in user_roles:
        return ""
    
    # For all other roles, only show vehicles owned by the user
    # First, find which Employee is linked to this user
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    if not employee:
        # If no linked employee, return no records
        return "1=0"
    
    # Return condition: only show vehicles where owner matches the employee
    return f"`tabVehicle`.employee = '{employee}'"

def request_for_machinery_maintenance_query_conditions(user):
    """Return conditions to filter Vehicle records based on user role"""
    
    # Check if user has Shared-Services-Vehicles role
    user_roles = frappe.get_roles(user)
    
    if "Shared-Services-Vehicles" in user_roles:
        return ""
    
    # For all other roles, only show vehicles owned by the user
    # First, find which Employee is linked to this user
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    if not employee:
        # If no linked employee, return no records
        return "1=0"
    
    # Return condition: only show vehicles where owner matches the employee
    return f"`tabRequest for Machinery Maintenance`.employee = '{employee}'"

def request_car_wash_query_conditions(user):
    """Return conditions to filter Vehicle records based on user role"""
    
    # Check if user has Shared-Services-Vehicles role
    user_roles = frappe.get_roles(user)
    
    if "Shared-Services-Vehicles" in user_roles:
        return ""
    
    # For all other roles, only show vehicles owned by the user
    # First, find which Employee is linked to this user
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    if not employee:
        # If no linked employee, return no records
        return "1=0"
    
    # Return condition: only show vehicles where owner matches the employee
    return f"`tabRequest Car Wash`.employee_name = '{employee}'"

def request_a_vehicle_reservation_query_conditions(user):
    """Return conditions to filter Vehicle records based on user role"""
    
    # Check if user has Shared-Services-Vehicles role
    user_roles = frappe.get_roles(user)
    
    if "Shared-Services-Vehicles" in user_roles:
        return ""
    
    # For all other roles, only show vehicles owned by the user
    # First, find which Employee is linked to this user
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    if not employee:
        # If no linked employee, return no records
        return "1=0"
    
    # Return condition: only show vehicles where owner matches the employee
    return f"`tabRequest a vehicle reservation`.employee_name = '{employee}'"

def technical_committee_receiving_minutes_query_conditions(user):
    """Return conditions to filter Vehicle records based on user role"""
    
    # Check if user has Shared-Services-Vehicles role
    user_roles = frappe.get_roles(user)
    
    if "Shared-Services-Vehicles" in user_roles:
        return ""
    
    # For all other roles, only show vehicles owned by the user
    # First, find which Employee is linked to this user
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    if not employee:
        # If no linked employee, return no records
        return "1=0"
    
    # Return condition: only show vehicles where owner matches the employee
    return f"`tabTechnical Committee Receiving Minutes`.driver = '{employee}'"

def request_for_an_oil_change_from_the_central_garage_query_conditions(user):
    """Return conditions to filter Vehicle records based on user role"""
    
    # Check if user has Shared-Services-Vehicles role
    user_roles = frappe.get_roles(user)
    
    if "Shared-Services-Vehicles" in user_roles:
        return ""
    
    # For all other roles, only show vehicles owned by the user
    # First, find which Employee is linked to this user
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    if not employee:
        # If no linked employee, return no records
        return "1=0"
    
    # Return condition: only show vehicles where owner matches the employee
    return f"`tabRequest for an Oil Change from the Central Garage`.full_name = '{employee}'"

def cleaning_company_performance_evaluation_query_conditions(user):
    """Return conditions to filter Vehicle records based on user role"""
    
    # Check if user has Shared-Services-Vehicles role
    user_roles = frappe.get_roles(user)
    
    if "Shared-Services-Stock" in user_roles:
        return ""
    
    # For all other roles, only show vehicles owned by the user
    # First, find which Employee is linked to this user
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    if not employee:
        # If no linked employee, return no records
        return "1=0"
    
    # Return condition: only show vehicles where owner matches the employee
    return f"`tabCleaning Company Performance Evaluation`.employee_name = '{employee}'"

def leave_application_query_conditions(user):
    """Return conditions to filter Vehicle records based on user role"""
    # Skip restrictions for privileged roles
    privileged_roles = {"HR Manager", "HR User","System Manager", "Administrator"}
    if set(frappe.get_roles(user)) & privileged_roles:
        return ""

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return f"`tabLeave Application`.owner = '{user}'"
    
    # Get subordinates
    subordinates = frappe.db.get_list(
        "Employee",
        filters={"reports_to": employee},
        pluck="name"
    )
    subordinates.append(employee)  # Include self
    
    emp_list = ", ".join(f"'{e}'" for e in subordinates)
    return f"(`tabLeave Application`.employee IN ({emp_list}) OR `tabLeave Application`.owner = '{user}')"

def attendance_request_query_conditions(user):
    """Return conditions to filter Vehicle records based on user role"""
    # Skip restrictions for privileged roles
    privileged_roles = {"HR Manager", "HR User","System Manager", "Administrator"}
    if set(frappe.get_roles(user)) & privileged_roles:
        return ""

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return f"`tabAttendance Request`.owner = '{user}'"
    
    # Get subordinates
    subordinates = frappe.db.get_list(
        "Employee",
        filters={"reports_to": employee},
        pluck="name"
    )
    subordinates.append(employee)  # Include self
    
    emp_list = ", ".join(f"'{e}'" for e in subordinates)
    return f"(`tabAttendance Request`.employee IN ({emp_list}) OR `tabAttendance Request`.owner = '{user}')"