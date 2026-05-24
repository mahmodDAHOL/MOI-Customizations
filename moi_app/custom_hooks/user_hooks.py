import frappe


def cleanup_employee_permissions_on_user_update(doc, method=None):
    """
    ON UPDATE: Remove existing Employee User Permissions for this user.
    Use ONLY during migration period – not needed long-term with prevention in place.
    """

    # Check if user has any of the specified roles
    target_roles = ["HR User", "HR Manager", "Asset manager", "Technician", "Shared-Services-Other",'Shared-Services-Vehicles','Shared-Services-Stock']

    # Get user's roles
    if hasattr(doc, 'roles') and doc.roles:
        user_roles = [role.role for role in doc.roles if hasattr(role, 'role')]
    else:
        # Fetch roles from database if not in document
        user_roles = frappe.get_roles(doc.name)

    # Check if user has ANY of the target roles
    has_target_role = False
    for role in user_roles:
        if role in target_roles:
            has_target_role = True
            break

    if not has_target_role:
        return
    # Skip new users (no permissions exist yet)
    if doc.get("__islocal"):
        return
    
    # Skip system accounts
    if doc.name in ("Administrator", "Guest"):
        return
    
    # Get permissions to delete
    permissions = frappe.get_all(
        "User Permission",
        filters={
            "user": doc.name,
            # "allow": "Employee"
        },
        pluck="name"
    )
    
    if not permissions:
        return
    
    # Delete safely using ORM
    for perm_name in permissions:
        try:
            frappe.delete_doc(
                "User Permission",
                perm_name,
                ignore_permissions=True,
                force=True
            )
        except Exception as e:
            frappe.log_error(
                title="User Permission Cleanup Failed",
                message=f"User: {doc.name} | Permission: {perm_name} | Error: {str(e)}"
            )
    
    # Audit log
    frappe.log_error(
        title="User Permission Auto-Cleanup",
        message=f"Removed {len(permissions)} Employee User Permission(s) for user: {doc.name}"
    )