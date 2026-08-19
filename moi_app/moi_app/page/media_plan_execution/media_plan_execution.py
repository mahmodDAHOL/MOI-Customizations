from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, today

DEFAULT_PAGE_LENGTH = 40
MAX_PAGE_LENGTH = 100
MAX_SCOPE_ROWS = 1000
MAX_HIERARCHY_EMPLOYEES = 5000
ACTIVE_PLAN_STATES = ("Approved", "Running")


@frappe.whitelist(methods=["GET", "POST"])
def get_assignments(
    query=None,
    scope_mode="mine",
    assigned_user=None,
    item_type=None,
    status=None,
    media_plan=None,
    limit_start=0,
    page_length=DEFAULT_PAGE_LENGTH,
):
    _require_execution_read_access()
    user = frappe.session.user
    is_administrator = user == "Administrator"
    hierarchy = get_reporting_hierarchy(user)
    visible_users = hierarchy["users"]
    scope_mode = "team" if str(scope_mode or "").lower() == "team" else "mine"
    selected_user = str(assigned_user or "").strip()
    selected_plan = str(media_plan or "").strip()

    if selected_user and not is_administrator and selected_user not in visible_users:
        frappe.throw(_("The selected user is outside your reporting hierarchy."), frappe.PermissionError)
    if selected_plan:
        plan_doc = frappe.get_doc("Media Plan", selected_plan)
        plan_doc.check_permission("read")
        if not is_administrator and not can_access_plan_owner(plan_doc.get("plan_owner"), user):
            frappe.throw(_("This Media Plan is outside your reporting hierarchy."), frappe.PermissionError)

    assignment_users = None
    if selected_user:
        assignment_users = {selected_user}
    elif scope_mode == "mine":
        assignment_users = {user}
    elif not is_administrator:
        assignment_users = set(visible_users)

    managed_plans = _managed_plan_names(None if is_administrator else visible_users, selected_plan)
    active_plans = _active_plan_names(selected_plan)
    can_read_production = (
        frappe.db.exists("DocType", "Media Production")
        and frappe.has_permission("Media Production", "read")
    )
    can_read_work_item = frappe.has_permission("Media Work Item", "read")
    items = []
    if can_read_production:
        items.extend(_execution_production(assignment_users, managed_plans, selected_plan, scope_mode))
    if can_read_work_item:
        items.extend(_execution_work_items(assignment_users, managed_plans, selected_plan, scope_mode))

    production_refs = {
        item.get("planned_row") for item in items
        if item.get("item_type") == "production" and item.get("planned_row")
    }
    work_item_refs = {
        item.get("planned_row") for item in items
        if item.get("item_type") == "work_item" and item.get("planned_row")
    }
    if can_read_production:
        items.extend(_planned_production(assignment_users, managed_plans, active_plans, production_refs, selected_plan, scope_mode))
    if can_read_work_item:
        items.extend(_planned_work_items(assignment_users, managed_plans, active_plans, work_item_refs, selected_plan, scope_mode))

    query_value = str(query or "").strip().lower()[:140]
    item_type = str(item_type or "").strip()
    status = str(status or "").strip()
    filtered = []
    for item in items:
        if item_type and item.get("item_type") != item_type:
            continue
        if status and item.get("status") != status:
            continue
        if query_value:
            haystack = " ".join(str(item.get(key) or "") for key in (
                "title", "name", "media_plan", "responsible_user", "entity", "material", "detail"
            )).lower()
            if query_value not in haystack:
                continue
        filtered.append(item)

    filtered.sort(key=lambda row: (str(row.get("end_date") or "9999-12-31"), str(row.get("title") or "")))
    limit_start = max(cint(limit_start), 0)
    page_length = min(max(cint(page_length) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)
    page = filtered[limit_start:limit_start + page_length]
    owner_users = visible_users if not is_administrator else {
        item.get("responsible_user") for item in filtered if item.get("responsible_user")
    }
    return {
        "items": page,
        "total": len(filtered),
        "has_more": limit_start + page_length < len(filtered),
        "next_start": limit_start + len(page),
        "can_create_production": can_read_production and frappe.has_permission("Media Production", "create"),
        "can_create_work_item": frappe.has_permission("Media Work Item", "create"),
        "user_options": _user_options(owner_users),
        "scope": {
            "is_administrator": is_administrator,
            "team_user_count": max(len(visible_users) - 1, 0),
            "scope_mode": scope_mode,
        },
    }


@frappe.whitelist(methods=["POST"])
def start_planned_item(item_type, row_name):
    item_type = str(item_type or "").strip()
    row_name = str(row_name or "").strip()
    if item_type == "production":
        return _start_planned_production(row_name)
    if item_type == "work_item":
        return _start_planned_work_item(row_name)
    frappe.throw(_("Invalid planned execution item type."))


def _start_planned_production(row_name):
    if not frappe.has_permission("Media Production", "create"):
        frappe.throw(_("Not permitted to create Media Production."), frappe.PermissionError)
    row = frappe.get_doc("Media Plan Production", row_name)
    plan = _validate_planned_row(row, "planned_production", row.get("media_production_responsible_user"))
    existing = frappe.db.get_value("Media Production", {"planned_production_row": row.name}, "name")
    if existing:
        return _execution_route("Media Production", existing)

    doc = frappe.new_doc("Media Production")
    values = {
        "execution_source": "Planned",
        "status": "Started",
        "media_plan": plan.name,
        "planned_production_row": row.name,
        "plan_owner": plan.get("plan_owner"),
        "actual_start_date": today(),
        "responsible_user": row.get("media_production_responsible_user"),
        "related_campaign": row.get("related_campaign") or row.get("related_campain"),
    }
    for fieldname in (
        "material", "material_name", "material_type", "media_coverage", "planned_quantity",
        "weight_percent", "executing_entity", "beneficiary_entity", "planned_start_date",
        "planned_end_date", "related_target_audience", "related_goal", "related_media_message",
        "related_event", "related_narrative", "notes",
    ):
        values[fieldname] = row.get(fieldname)
    _set_existing_fields(doc, values)
    doc.insert()
    return _execution_route(doc.doctype, doc.name)


def _start_planned_work_item(row_name):
    if not frappe.has_permission("Media Work Item", "create"):
        frappe.throw(_("Not permitted to create Media Work Item."), frappe.PermissionError)
    meta = frappe.get_meta("Media Work Item")
    if not meta.has_field("planned_work_item_row"):
        frappe.throw(_("Run the Media Plan execution setup before starting planned work items."))
    row = frappe.get_doc("Media Planned Work Item", row_name)
    plan = _validate_planned_row(row, "planned_work_items", row.get("workitem_responsible_user"))
    existing = frappe.db.get_value("Media Work Item", {"planned_work_item_row": row.name}, "name")
    if existing:
        return _execution_route("Media Work Item", existing)

    doc = frappe.new_doc("Media Work Item")
    values = {
        "execution_source": "Planned",
        "status": "Started",
        "media_plan": plan.name,
        "planned_work_item_row": row.name,
        "assigned_user": row.get("workitem_responsible_user"),
        "start_date": row.get("planned_start_date") or today(),
        "work_item_type": row.get("work_item_type"),
        "work_item_title": row.get("work_item_title"),
        "entity": row.get("related_entity"),
        "end_date": row.get("planned_end_date"),
        "media_campaign": row.get("related_campaign"),
        "media_event": row.get("related_event"),
        "expected_output": row.get("expected_output"),
        "related_workitem_target_audience": row.get("related_target_audience"),
        "related_workitem_goal": row.get("related_workitem_goal"),
        "related_workitem_message": row.get("related_workitem_message"),
        "related_workitem_risk": row.get("related_risk"),
        "related_workitem_opportunity": row.get("related_opportunity"),
        "related_workitem_narrative": row.get("related_narrative"),
        "notes": row.get("notes"),
    }
    _set_existing_fields(doc, values)
    doc.insert()
    return _execution_route(doc.doctype, doc.name)


def _validate_planned_row(row, parentfield, responsible_user):
    if row.parenttype != "Media Plan" or row.parentfield != parentfield:
        frappe.throw(_("Invalid planned execution row."))
    plan = frappe.get_doc("Media Plan", row.parent)
    plan.check_permission("read")
    state = _plan_state(plan)
    if state not in ACTIVE_PLAN_STATES:
        frappe.throw(_("Only Approved or Running Media Plans can start execution."))
    user = frappe.session.user
    if user != "Administrator":
        visible_users = get_reporting_hierarchy(user)["users"]
        allowed = responsible_user in visible_users or plan.get("plan_owner") in visible_users
        if not allowed:
            frappe.throw(_("This planned item is outside your reporting hierarchy."), frappe.PermissionError)
    return plan


def _execution_production(users, managed_plans, selected_plan, scope_mode):
    if not frappe.db.exists("DocType", "Media Production"):
        return []
    fields = [
        "name", "execution_source", "status", "priority", "media_plan", "planned_production_row",
        "responsible_user", "material", "material_name", "material_type", "executing_entity",
        "beneficiary_entity", "planned_start_date", "planned_end_date", "completion_percent", "modified",
    ]
    rows = _scoped_execution_rows("Media Production", "responsible_user", users, managed_plans, selected_plan, scope_mode, fields)
    return [{
        "key": "production:" + row.name,
        "item_type": "production",
        "doctype": "Media Production",
        "name": row.name,
        "planned_row": row.get("planned_production_row"),
        "execution_source": row.get("execution_source"),
        "title": row.get("material_name") or row.get("material") or row.name,
        "detail": row.get("material_type"),
        "material": row.get("material"),
        "media_plan": row.get("media_plan"),
        "responsible_user": row.get("responsible_user"),
        "entity": row.get("executing_entity"),
        "beneficiary_entity": row.get("beneficiary_entity"),
        "start_date": row.get("planned_start_date"),
        "end_date": row.get("planned_end_date"),
        "status": row.get("status") or "Draft",
        "progress": row.get("completion_percent") or 0,
        "priority": row.get("priority"),
        "can_start": False,
    } for row in rows]


def _execution_work_items(users, managed_plans, selected_plan, scope_mode):
    meta = frappe.get_meta("Media Work Item")
    fields = [
        "name", "execution_source", "status", "priority", "media_plan", "assigned_user",
        "work_item_title", "work_item_type", "entity", "start_date", "end_date", "progress", "modified",
    ]
    if meta.has_field("planned_work_item_row"):
        fields.append("planned_work_item_row")
    rows = _scoped_execution_rows("Media Work Item", "assigned_user", users, managed_plans, selected_plan, scope_mode, fields)
    return [{
        "key": "work_item:" + str(row.name),
        "item_type": "work_item",
        "doctype": "Media Work Item",
        "name": str(row.name),
        "planned_row": row.get("planned_work_item_row"),
        "execution_source": row.get("execution_source"),
        "title": row.get("work_item_title") or row.get("work_item_type") or str(row.name),
        "detail": row.get("work_item_type"),
        "media_plan": row.get("media_plan"),
        "responsible_user": row.get("assigned_user"),
        "entity": row.get("entity"),
        "start_date": row.get("start_date"),
        "end_date": row.get("end_date"),
        "status": row.get("status") or "Draft",
        "progress": row.get("progress") or 0,
        "priority": row.get("priority"),
        "can_start": False,
    } for row in rows]


def _planned_production(users, managed_plans, active_plans, existing_refs, selected_plan, scope_mode):
    fields = [
        "name", "parent", "material", "material_type", "planned_quantity", "executing_entity",
        "beneficiary_entity", "media_production_responsible_user", "planned_start_date", "planned_end_date",
    ]
    meta = frappe.get_meta("Media Plan Production")
    fields = [field for field in fields if field in {"name", "parent"} or meta.has_field(field)]
    rows = _scoped_planned_rows("Media Plan Production", "planned_production", "media_production_responsible_user", users, managed_plans, active_plans, selected_plan, scope_mode, fields)
    return [{
        "key": "planned_production:" + row.name,
        "item_type": "production",
        "doctype": "Media Plan Production",
        "name": None,
        "planned_row": row.name,
        "execution_source": "Planned",
        "title": row.get("material") or _("Planned Media Production"),
        "detail": row.get("material_type"),
        "material": row.get("material"),
        "media_plan": row.parent,
        "responsible_user": row.get("media_production_responsible_user"),
        "entity": row.get("executing_entity"),
        "beneficiary_entity": row.get("beneficiary_entity"),
        "start_date": row.get("planned_start_date"),
        "end_date": row.get("planned_end_date"),
        "status": "Planned",
        "progress": 0,
        "priority": None,
        "can_start": True,
    } for row in rows if row.name not in existing_refs]


def _planned_work_items(users, managed_plans, active_plans, existing_refs, selected_plan, scope_mode):
    fields = [
        "name", "parent", "work_item_title", "work_item_type", "workitem_responsible_user",
        "related_entity", "planned_start_date", "planned_end_date",
    ]
    rows = _scoped_planned_rows("Media Planned Work Item", "planned_work_items", "workitem_responsible_user", users, managed_plans, active_plans, selected_plan, scope_mode, fields)
    return [{
        "key": "planned_work_item:" + row.name,
        "item_type": "work_item",
        "doctype": "Media Planned Work Item",
        "name": None,
        "planned_row": row.name,
        "execution_source": "Planned",
        "title": row.get("work_item_title") or row.get("work_item_type") or _("Planned Media Work Item"),
        "detail": row.get("work_item_type"),
        "media_plan": row.parent,
        "responsible_user": row.get("workitem_responsible_user"),
        "entity": row.get("related_entity"),
        "start_date": row.get("planned_start_date"),
        "end_date": row.get("planned_end_date"),
        "status": "Planned",
        "progress": 0,
        "priority": None,
        "can_start": True,
    } for row in rows if row.name not in existing_refs]


def _scoped_execution_rows(doctype, user_field, users, managed_plans, selected_plan, scope_mode, fields):
    base = {}
    if selected_plan:
        base["media_plan"] = selected_plan
    rows = []
    if users is not None:
        filters = dict(base)
        filters[user_field] = ["in", sorted(users)]
        rows.extend(frappe.get_all(doctype, filters=filters, fields=fields, limit_page_length=MAX_SCOPE_ROWS))
    else:
        rows.extend(frappe.get_all(doctype, filters=base, fields=fields, limit_page_length=MAX_SCOPE_ROWS))
    if scope_mode == "team" and managed_plans and not selected_plan:
        rows.extend(frappe.get_all(doctype, filters={"media_plan": ["in", sorted(managed_plans)]}, fields=fields, limit_page_length=MAX_SCOPE_ROWS))
    return _dedupe_rows(rows)


def _scoped_planned_rows(doctype, parentfield, user_field, users, managed_plans, active_plans, selected_plan, scope_mode, fields):
    if not active_plans:
        return []
    base = {"parenttype": "Media Plan", "parentfield": parentfield, "parent": ["in", sorted(active_plans)]}
    rows = []
    if users is not None:
        user_filters = dict(base)
        user_filters[user_field] = ["in", sorted(users)]
        rows.extend(frappe.get_all(doctype, filters=user_filters, fields=fields, limit_page_length=MAX_SCOPE_ROWS))
    else:
        rows.extend(frappe.get_all(doctype, filters=base, fields=fields, limit_page_length=MAX_SCOPE_ROWS))
    if scope_mode == "team" and managed_plans:
        plan_filters = dict(base)
        plan_filters["parent"] = ["in", sorted(set(active_plans).intersection(managed_plans))]
        rows.extend(frappe.get_all(doctype, filters=plan_filters, fields=fields, limit_page_length=MAX_SCOPE_ROWS))
    return _dedupe_rows(rows)


def _managed_plan_names(users, selected_plan=None):
    if selected_plan:
        return {selected_plan}
    filters = {}
    if users is not None:
        filters["plan_owner"] = ["in", sorted(users)]
    return set(frappe.get_all("Media Plan", filters=filters, pluck="name", limit_page_length=MAX_SCOPE_ROWS))


def _active_plan_names(selected_plan=None):
    meta = frappe.get_meta("Media Plan")
    workflow = frappe.db.get_value("Workflow", {"document_type": "Media Plan", "is_active": 1}, ["name", "workflow_state_field"], as_dict=True)
    state_field = workflow.get("workflow_state_field") if workflow else "status"
    filters = {}
    if selected_plan:
        filters["name"] = selected_plan
    if meta.has_field(state_field):
        filters[state_field] = ["in", list(ACTIVE_PLAN_STATES)]
    return set(frappe.get_all("Media Plan", filters=filters, pluck="name", limit_page_length=MAX_SCOPE_ROWS))


def _plan_state(plan):
    workflow = frappe.db.get_value("Workflow", {"document_type": "Media Plan", "is_active": 1}, "workflow_state_field")
    return plan.get(workflow or "status") or plan.get("workflow_state") or plan.get("status") or "Draft"


def _validate_scope_doc(row, users, managed_plans):
    return users is None or row.get("responsible_user") in users or row.get("media_plan") in managed_plans


def _dedupe_rows(rows):
    result = []
    seen = set()
    for row in rows:
        if row.name not in seen:
            seen.add(row.name)
            result.append(row)
    return result


def _set_existing_fields(doc, values):
    meta = frappe.get_meta(doc.doctype)
    for fieldname in values:
        if meta.has_field(fieldname) and values.get(fieldname) is not None:
            doc.set(fieldname, values.get(fieldname))


def _execution_route(doctype, name):
    return {
        "success": True,
        "doctype": doctype,
        "name": name,
        "route": "/app/" + frappe.scrub(doctype).replace("_", "-") + "/" + str(name),
    }


def _user_options(users):
    users = {user for user in users or [] if user}
    if not users:
        return []
    rows = frappe.get_all("User", filters={"name": ["in", sorted(users)]}, fields=["name", "full_name"], limit_page_length=len(users))
    return [{"value": row.name, "label": row.full_name or row.name} for row in rows]


def _require_execution_read_access():
    if not (
        frappe.has_permission("Media Work Item", "read")
        or (frappe.db.exists("DocType", "Media Production") and frappe.has_permission("Media Production", "read"))
    ):
        frappe.throw(_("Not permitted to view Media Plan execution."), frappe.PermissionError)


def get_reporting_hierarchy(user=None):
    """Return the current user and every active subordinate recursively."""
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


def can_access_plan_owner(plan_owner, user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    plan_owner = str(plan_owner or "").strip()
    if not plan_owner:
        return False
    return plan_owner in get_reporting_hierarchy(user)["users"]
