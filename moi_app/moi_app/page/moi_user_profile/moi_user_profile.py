import re
import frappe
from frappe import _
from frappe.utils import cint, flt, pretty_date, today, getdate


ENERGY_TYPE = "Auto"


@frappe.whitelist()
def get_profile_data():
    user = frappe.session.user

    if user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    user_doc = frappe.get_doc("User", user)

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["name", "department", "designation", "employee_name"],
        as_dict=True,
    )

    approved, pending, rejected = get_leave_summary(employee)

    return {
        "user": user,
        "employee": employee.name if employee else "",
        "full_name": user_doc.full_name or user,
        "user_image": user_doc.user_image or "/assets/frappe/images/ui/avatar.png",
        "department": employee.department if employee else "-",
        "designation": employee.designation if employee else "-",
        "ministry": _("Ministry of Information"),

        "energy_points": get_energy_points(user, ENERGY_TYPE),
        "monthly_points": get_monthly_points(user, ENERGY_TYPE),
        "rank": get_rank(user, ENERGY_TYPE),
        "monthly_rank": get_monthly_rank(user, ENERGY_TYPE),
        "pending_leaves": pending,

        "attendance_compliance": 0,
        "expected_hours": "-",
        "actual_hours": "-",
        "unjustified_hours": "-",
        "late_entry_hours": "-",

        "leave_summary": {
            "approved": approved,
            "pending": pending,
            "rejected": rejected,
        },

        "leave_balances": get_leave_balances(employee),

        "tasks": get_tasks(user),
        "chart_data": get_energy_chart_data(user, ENERGY_TYPE),
        "recent_activity": get_recent_activity(user, ENERGY_TYPE),

        "direction": "rtl" if frappe.local.lang in ["ar"] else "ltr",
        "lang": frappe.local.lang,
        "labels": get_labels(),
    }


# ---------------------------------------------------------
# ENERGY POINTS
# ---------------------------------------------------------

def get_energy_points(user, energy_type="Auto"):
    return cint(frappe.db.sql("""
        SELECT IFNULL(SUM(points), 0)
        FROM `tabEnergy Point Log`
        WHERE user = %s
        AND type = %s
    """, (user, energy_type))[0][0] or 0)


def get_monthly_points(user, energy_type="Auto"):
    return cint(frappe.db.sql("""
        SELECT IFNULL(SUM(points), 0)
        FROM `tabEnergy Point Log`
        WHERE user = %s
        AND type = %s
        AND MONTH(creation) = MONTH(CURDATE())
        AND YEAR(creation) = YEAR(CURDATE())
    """, (user, energy_type))[0][0] or 0)


def get_energy_chart_data(user, energy_type="Auto"):
    rows = frappe.db.sql("""
        SELECT
            DATE(creation) AS date,
            IFNULL(SUM(points), 0) AS points
        FROM `tabEnergy Point Log`
        WHERE user = %s
        AND type = %s
        AND creation >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY DATE(creation)
        ORDER BY DATE(creation)
    """, (user, energy_type), as_dict=True)

    return [
        {
            "date": str(row.date),
            "points": cint(row.points)
        }
        for row in rows
    ]


def get_recent_activity(user, energy_type="Auto"):
    rows = frappe.db.sql("""
        SELECT
            creation,
            points,
            reference_doctype,
            reference_name,
            type
        FROM `tabEnergy Point Log`
        WHERE user = %s
        AND type = %s
        ORDER BY creation DESC
        LIMIT 6
    """, (user, energy_type), as_dict=True)

    activity = []

    for row in rows:
        title = _("Energy point activity")

        if row.reference_doctype:
            title = _(row.reference_doctype)

        points = cint(row.points)

        activity.append({
            "title": title,
            "time": pretty_date(row.creation),
            "points": f"+{points}" if points > 0 else str(points),
            "reference_doctype": row.reference_doctype or "",
            "reference_name": row.reference_name or "",
        })

    return activity


def get_rank(user, energy_type="Auto"):
    rows = frappe.db.sql("""
        SELECT user, IFNULL(SUM(points), 0) AS total_points
        FROM `tabEnergy Point Log`
        WHERE type = %s
        GROUP BY user
        ORDER BY total_points DESC
    """, (energy_type,), as_dict=True)

    for index, row in enumerate(rows, start=1):
        if row.user == user:
            return index

    return 0


def get_monthly_rank(user, energy_type="Auto"):
    rows = frappe.db.sql("""
        SELECT user, IFNULL(SUM(points), 0) AS total_points
        FROM `tabEnergy Point Log`
        WHERE type = %s
        AND MONTH(creation) = MONTH(CURDATE())
        AND YEAR(creation) = YEAR(CURDATE())
        GROUP BY user
        ORDER BY total_points DESC
    """, (energy_type,), as_dict=True)

    for index, row in enumerate(rows, start=1):
        if row.user == user:
            return index

    return 0


# ---------------------------------------------------------
# LEAVES
# ---------------------------------------------------------

def get_leave_summary(employee):
    if not employee:
        return 0, 0, 0

    approved = frappe.db.count("Leave Application", {
        "employee": employee.name,
        "workflow_state": "Approved"
    })

    rejected = frappe.db.count("Leave Application", {
        "employee": employee.name,
        "workflow_state": "Rejected"
    })

    pending = frappe.db.count("Leave Application", {
        "employee": employee.name,
        "workflow_state": ["not in", ["Approved", "Rejected"]]
    })

    return cint(approved), cint(pending), cint(rejected)


def get_leave_balances(employee):
    """
    Returns allocated and remaining leave balance per Leave Type
    for the current employee.

    Output example:
    [
        {
            "leave_type": "Annual Leave",
            "total_allocated": 20,
            "used_leaves": 3,
            "pending_leaves": 1,
            "available_leaves": 16
        }
    ]
    """

    if not employee:
        return []

    employee_name = employee.name
    current_date = getdate(today())

    allocations = frappe.get_all(
        "Leave Allocation",
        filters={
            "employee": employee_name,
            "docstatus": 1,
            "from_date": ["<=", current_date],
            "to_date": [">=", current_date],
        },
        fields=[
            "name",
            "leave_type",
            "total_leaves_allocated",
            "from_date",
            "to_date",
        ],
        order_by="leave_type asc",
    )

    balances = []

    for allocation in allocations:
        leave_type = allocation.leave_type
        from_date = allocation.from_date
        to_date = allocation.to_date

        total_allocated = flt(allocation.total_leaves_allocated)

        used_leaves = get_used_leaves(
            employee_name=employee_name,
            leave_type=leave_type,
            from_date=from_date,
            to_date=to_date,
        )

        pending_leaves = get_pending_leaves(
            employee_name=employee_name,
            leave_type=leave_type,
            from_date=from_date,
            to_date=to_date,
        )

        available_leaves = total_allocated - used_leaves - pending_leaves

        balances.append({
            "leave_type": leave_type,
            "total_allocated": format_number(total_allocated),
            "used_leaves": format_number(used_leaves),
            "pending_leaves": format_number(pending_leaves),
            "available_leaves": format_number(available_leaves),
        })

    return balances


def get_used_leaves(employee_name, leave_type, from_date, to_date):
    result = frappe.db.sql("""
        SELECT IFNULL(SUM(total_leave_days), 0)
        FROM `tabLeave Application`
        WHERE employee = %s
        AND leave_type = %s
        AND docstatus = 1
        AND status = 'Approved'
        AND from_date <= %s
        AND to_date >= %s
    """, (employee_name, leave_type, to_date, from_date))[0][0]

    return flt(result or 0)


def get_pending_leaves(employee_name, leave_type, from_date, to_date):
    result = frappe.db.sql("""
        SELECT IFNULL(SUM(total_leave_days), 0)
        FROM `tabLeave Application`
        WHERE employee = %s
        AND leave_type = %s
        AND docstatus = 0
        AND status IN ('Open', 'Pending Approval')
        AND from_date <= %s
        AND to_date >= %s
    """, (employee_name, leave_type, to_date, from_date))[0][0]

    return flt(result or 0)


def format_number(value):
    value = flt(value)

    if value == int(value):
        return int(value)

    return round(value, 3)


# ---------------------------------------------------------
# TASKS
# ---------------------------------------------------------

def get_tasks(user):
    todos = frappe.get_all(
        "ToDo",
        filters={
            "allocated_to": user,
            "status": ["!=", "Cancelled"],
        },
        fields=[
            "name",
            "description",
            "status",
            "priority",
            "date",
            "reference_type",
            "reference_name",
        ],
        order_by="modified desc",
        limit=8,
    )

    tasks = []

    for row in todos:
        title = clean_html(row.description) or row.reference_name or _("Task")

        tasks.append({
            "name": row.name,
            "title": title,
            "status": row.status or _("Open"),
            "priority": row.priority or _("Medium"),
            "due_date": str(row.date) if row.date else "-",
            "expected_closure": str(row.date) if row.date else "-",
            "reference_type": row.reference_type or "",
            "reference_name": row.reference_name or "",
            "status_class": get_task_status_class(row.status),
            "priority_class": get_task_priority_class(row.priority),
        })

    return tasks


def clean_html(value):
    if not value:
        return ""

    value = re.sub(r"<[^>]*>", "", value)
    value = value.replace("&nbsp;", " ")
    value = value.strip()

    return value


def get_task_status_class(status):
    status = (status or "").lower()

    if "closed" in status or "completed" in status:
        return "moi-task-status-closed"

    if "cancelled" in status:
        return "moi-task-status-cancelled"

    return "moi-task-status-open"


def get_task_priority_class(priority):
    priority = (priority or "").lower()

    if "high" in priority:
        return "moi-task-priority-high"

    if "low" in priority:
        return "moi-task-priority-low"

    return "moi-task-priority-medium"


# ---------------------------------------------------------
# LABELS
# ---------------------------------------------------------

def get_labels():
    return {
        "active_employee": _("Active Employee"),
        "edit_profile": _("Edit Profile"),
        "user_settings": _("User Settings"),
        "leaderboard": _("Leaderboard"),

        "energy_points": _("Energy Points"),
        "rank": _("Rank"),
        "monthly_rank": _("Monthly Rank"),
        "pending_leaves": _("Pending Leaves"),

        "this_month": _("This Month"),
        "overall_rank": _("Overall Rank"),

        "attendance_compliance": _("Attendance Compliance"),
        "expected_hours": _("Expected Hours"),
        "actual_hours": _("Actual + Leave"),
        "unjustified_hours": _("Unjustified"),
        "late_entry_hours": _("Late Entry"),

        "leave_summary": _("Leave Summary"),
        "approved": _("Approved"),
        "pending": _("Pending"),
        "rejected": _("Rejected"),

        "leave_balances": _("Leave Balances"),
        "leave_type": _("Leave Type"),
        "total_allocated": _("Total Allocated"),
        "used_leaves": _("Used"),
        "available_leaves": _("Available"),
        "pending_approval": _("Pending Approval"),

        "recent_activity": _("Recent Activity"),
        "activity_subtitle": _("Latest employee activity"),

        "chart_title": _("Performance Overview"),
        "chart_subtitle": _("Energy points during last days"),

        "daily": _("Daily"),
        "weekly": _("Weekly"),
        "monthly": _("Monthly"),

        "view_all": _("View All"),
        "no_activity": _("No activity to show"),
        "no_chart_data": _("No chart data available"),

        "my_tasks": _("My Tasks"),
        "tasks_subtitle": _("Assigned tasks and expected closure dates"),
        "task_status": _("Status"),
        "task_due": _("Expected Closure"),
        "task_priority": _("Priority"),
        "view_task": _("Open"),
        "no_tasks": _("No tasks assigned"),
    }