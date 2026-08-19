from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint


MAX_PAGE_LENGTH = 100
DEFAULT_PAGE_LENGTH = 30
MAX_HIERARCHY_EMPLOYEES = 10000
SEARCHABLE_FIELDS = ("name", "plan_name", "plan_name_ar", "project")


@frappe.whitelist(methods=["GET", "POST"])
def get_plans(
    query: str | None = None,
    plan_owner: str | None = None,
    workflow_state: str | None = None,
    limit_start: int = 0,
    page_length: int = DEFAULT_PAGE_LENGTH,
):
    """Return only Media Plans owned by the user or their reporting tree."""
    if not frappe.has_permission("Media Plan", "read"):
        frappe.throw(_("Not permitted to view Media Plans."), frappe.PermissionError)

    current_user = frappe.session.user
    is_administrator = current_user == "Administrator"
    hierarchy = get_reporting_hierarchy(current_user)
    visible_users = hierarchy["users"]

    requested_owner = str(plan_owner or "").strip()
    if requested_owner and not is_administrator and requested_owner not in visible_users:
        frappe.throw(_("The selected Plan Owner is outside your reporting hierarchy."), frappe.PermissionError)

    limit_start = max(cint(limit_start), 0)
    page_length = min(max(cint(page_length) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)
    query = str(query or "").strip()[:140]
    workflow_state = str(workflow_state or "").strip()[:140]

    media_plan_meta = frappe.get_meta("Media Plan")
    active_workflow = frappe.db.get_value(
        "Workflow",
        {"document_type": "Media Plan", "is_active": 1},
        ["name", "workflow_state_field"],
        as_dict=True,
    )
    state_field = (
        active_workflow.get("workflow_state_field")
        if active_workflow and active_workflow.get("workflow_state_field")
        else "workflow_state"
    )

    desired_fields = [
        "name",
        "docstatus",
        "modified",
        "plan_name",
        "plan_name_ar",
        "project",
        "plan_owner",
        "start_date",
        "end_date",
        "priority",
        "status",
        state_field,
    ]
    fields = []
    for fieldname in desired_fields:
        if fieldname in {"name", "docstatus", "modified"} or media_plan_meta.has_field(fieldname):
            if fieldname not in fields:
                fields.append(fieldname)

    filters = {}
    if requested_owner:
        filters["plan_owner"] = requested_owner
    elif not is_administrator:
        filters["plan_owner"] = ["in", sorted(visible_users)]

    if workflow_state and media_plan_meta.has_field(state_field):
        filters[state_field] = workflow_state

    or_filters = None
    if query:
        like_value = "%" + query + "%"
        or_filters = {}
        for searchable_field in SEARCHABLE_FIELDS:
            if searchable_field == "name" or media_plan_meta.has_field(searchable_field):
                or_filters[searchable_field] = ["like", like_value]

    plans = frappe.get_all(
        "Media Plan",
        fields=fields,
        filters=filters,
        or_filters=or_filters,
        order_by="modified desc",
        limit_start=limit_start,
        limit_page_length=page_length + 1,
    )
    has_more = len(plans) > page_length
    plans = plans[:page_length]

    plan_owner_values = []
    for plan in plans:
        owner_value = plan.get("plan_owner")
        if owner_value and owner_value not in plan_owner_values:
            plan_owner_values.append(owner_value)
    # Keep the active owner filter available even when it returns no plans.
    if requested_owner and requested_owner not in plan_owner_values:
        plan_owner_values.append(requested_owner)

    owner_options = _owner_options(
        None if is_administrator else visible_users,
        hierarchy["employee_names"],
        extra_users=plan_owner_values,
    )
    states = _workflow_states(active_workflow.get("name") if active_workflow else None)

    return {
        "plans": plans,
        "has_more": has_more,
        "next_start": limit_start + len(plans),
        "can_create": frappe.has_permission("Media Plan", "create"),
        "current_user": current_user,
        "owner_options": owner_options,
        "workflow_states": states,
        "scope": {
            "is_administrator": is_administrator,
            "team_user_count": max(len(visible_users) - 1, 0),
            "team_employee_count": hierarchy["subordinate_employee_count"],
        },
        "workflow_state_field": state_field,
    }


def get_reporting_hierarchy(user: str | None = None):
    """Return the user plus users mapped to every descendant Employee."""
    user = user or frappe.session.user
    visible_users = {user}
    employee_names = {}

    if not frappe.db.table_exists("Employee"):
        return {
            "users": visible_users,
            "employee_names": employee_names,
            "subordinate_employee_count": 0,
        }

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "user_id", "reports_to"],
        limit_page_length=MAX_HIERARCHY_EMPLOYEES,
    )
    children_by_manager = {}
    roots = []

    for employee in employees:
        employee_name = employee.get("name")
        reports_to = employee.get("reports_to")
        employee_user = employee.get("user_id")
        if reports_to:
            children_by_manager.setdefault(reports_to, []).append(employee)
        if employee_user == user and employee_name:
            roots.append(employee_name)
            employee_names[user] = employee.get("employee_name") or user

    visited_employees = set(roots)
    queue = list(roots)
    subordinate_employee_count = 0

    while queue:
        manager_employee = queue.pop(0)
        for subordinate in children_by_manager.get(manager_employee, []):
            subordinate_name = subordinate.get("name")
            if not subordinate_name or subordinate_name in visited_employees:
                continue
            visited_employees.add(subordinate_name)
            queue.append(subordinate_name)
            subordinate_employee_count += 1
            subordinate_user = subordinate.get("user_id")
            if subordinate_user:
                visible_users.add(subordinate_user)
                employee_names[subordinate_user] = subordinate.get("employee_name") or subordinate_user

    return {
        "users": visible_users,
        "employee_names": employee_names,
        "subordinate_employee_count": subordinate_employee_count,
    }


def can_access_plan_owner(plan_owner: str | None, user: str | None = None) -> bool:
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    plan_owner = str(plan_owner or "").strip()
    if not plan_owner:
        return False
    return plan_owner in get_reporting_hierarchy(user)["users"]


def _owner_options(visible_users, employee_names, extra_users=None):
    users = set(visible_users or [])
    for extra_user in extra_users or []:
        if extra_user:
            users.add(extra_user)
    if not users:
        return []

    user_rows = frappe.get_all(
        "User",
        filters={"name": ["in", sorted(users)]},
        fields=["name", "full_name"],
        order_by="full_name asc",
        limit_page_length=max(len(users), 1),
    )
    options = []
    for user_row in user_rows:
        user_name = user_row.get("name")
        options.append({
            "value": user_name,
            "label": employee_names.get(user_name) or user_row.get("full_name") or user_name,
        })
    return options


def _workflow_states(workflow_name):
    if not workflow_name:
        return []
    states = frappe.get_all(
        "Workflow Document State",
        filters={"parent": workflow_name, "parenttype": "Workflow"},
        fields=["state", "idx"],
        order_by="idx asc",
        limit_page_length=100,
    )
    result = []
    for state in states:
        state_name = state.get("state")
        if state_name and state_name not in result:
            result.append(state_name)
    return result
