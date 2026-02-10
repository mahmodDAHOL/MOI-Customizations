from datetime import date

# Get today's date
today = date.today()

from_date = None
to_date = None
if not from_date:
    from_date = f"{frappe.utils.getdate(frappe.utils.today()).year}-01-01"
if not to_date:
    to_date = f"{frappe.utils.getdate(frappe.utils.today()).year}-12-31"

leave_type = "إجازة إدارية"




employees = frappe.get_all(
    "Employee",
    filters={
        "company": "Ministry of Information",
        "status": "Active"
    },
    fields=["name", "employee_name", "date_of_joining", "date_of_birth"]
)
            
            
            

if not employees:
    frappe.msgprint("No active employees found.")
    exit()

created_allocations = 0
skipped_employees = []

for emp in employees:
    # Calculate years of service
    doj = emp.date_of_joining
    years_service = (today - doj).days / 365.25 if doj else 0
    
    # Calculate age (if date_of_birth available)
    dob = emp.date_of_birth
    age = (today - dob).days / 365.25 if dob else 0
    
    # Assign new_leaves based on rules
    if years_service < 5:
        new_leaves = 15
    elif 5 <= years_service < 10:
        new_leaves = 21
    elif 10 <= years_service < 20:
        new_leaves = 26
    else:  # ≥20 years service OR age > 50
        if years_service >= 20 or age > 50:
            new_leaves = 30
        else:
            print(f"{emp.employee_name=} {dob=} ")
            new_leaves = 26  # fallback (shouldn't occur)

    try:
        # Check if allocation already exists for this employee in the period
        existing_allocation = frappe.db.exists(
            "Leave Allocation",
            {
                "employee": emp.name,
                "leave_type": leave_type,
                "docstatus": ("<", 2)  # Not cancelled
            }
        )

        if existing_allocation:
            print(f"Allocation already exists for {emp.name} ({emp.employee_name}). Skipping.")
            skipped_employees.append(f"{emp.name} - Allocation already exists")
            continue

        # Create new Leave Allocation
        allocation = frappe.get_doc({
            "doctype": "Leave Allocation",
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "new_leaves_allocated": new_leaves,
            "description": f"Allocated {new_leaves} {leave_type}(s) via script."
        })

        # Insert and submit
        allocation.insert()
        allocation.submit()
        created_allocations += 1
        print(f"Allocated {new_leaves} {leave_type}(s) to {emp.name} ({emp.employee_name})")

    except Exception as e:
        error_msg = f"Failed to allocate leave for {emp.name}: {str(e)}"
        frappe.log_error(error_msg, "Leave Allocation Script Error")
        print(error_msg)
        skipped_employees.append(f"{emp.name} - Error: {str(e)}")

# # Commit all changes
# frappe.db.commit()

# Report results
message = f"Successfully allocated {leave_type} to {created_allocations} employee(s)."
if skipped_employees:
    message += f"\nSkipped {len(skipped_employees)} employee(s):\n" + "\n".join(skipped_employees)

frappe.msgprint(message)
print(message) # Also print to console if run via bench execute