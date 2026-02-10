import frappe

@frappe.whitelist()
def get_administration_tree(office=None, department=None, section=None, company=None):
    if department:
        departments = frappe.get_all("Department", fields=["name"], filters={"name":["like", f"%{department}%"]}, order_by="name")
    else:
        departments = frappe.get_all("Department", fields=["name"], filters={"company":["like", f"%{company}%"]}, order_by="name")
    result = []

    for dept in departments:
        # Get offices (is_group=1) under this department
        office_filters = {"department": dept.name}
        if office:
            office_filters["name"] = ["like", f"%{office}%"]
        
        offices = frappe.get_all("Office", 
            filters=office_filters,
            fields=["name"]
        )

        dept_data = {"name": dept.name, "offices": [], "emp_num": frappe.db.count("Employee", filters={"department": dept.name})}

        for off in offices:
            # Get sections (is_group=0, children of office)
            section_filters = {
                "office": off.name,
            }
            if section:
                section_filters["name"] = ["like", f"%{section}%"]

            sections = frappe.get_all("section",
                filters=section_filters,
                fields=["name"]
            )

            # Include office if it has sections OR no section filter
            if sections or not section:
                dept_data["offices"].append({
                    "name": off.name,
                    "sections": [
                        {"name": sec.name, "emp_num": frappe.db.count("Employee", filters={"custom_section": sec.name})}
                        for sec in sections
                    ],
                    "emp_num": frappe.db.count("Employee", filters={"custom_office": off.name})
                })

        # if dept_data["offices"]:
        result.append(dept_data)

    return result