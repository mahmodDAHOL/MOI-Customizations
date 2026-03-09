import frappe


def cleanup_employee_permissions_on_user_update(doc, method=None):
    """
    ON UPDATE: Remove existing Employee User Permissions for this user.
    Use ONLY during migration period – not needed long-term with prevention in place.
    """
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
            "allow": "Employee"
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