from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from press_affairs_app.moi.page.manage_media_plan.manage_media_plan import can_access_plan_owner


MAIN_FIELDS = (
    "plan_name",
    "plan_name_ar",
    "project",
    "plan_owner",
    "start_date",
    "end_date",
    "priority",
    "description",
)

MAX_PAYLOAD_BYTES = 1024 * 1024
MAX_SOURCE_ROWS_PER_TABLE = 200
MAX_SIMPLE_ROWS_PER_TABLE = 100
MAX_GOALS_PER_SOURCE = 1
MAX_AUDIENCES_PER_SOURCE = 1
MAX_TARGETING_RELATIONS = 2000
MAX_TEXT_VALUE_LENGTH = 50000

SOURCE_CONFIG = {
    "planned_production": {
        "doctype": "Media Plan Production",
    },
    "planned_work_items": {
        "doctype": "Media Planned Work Item",
    },
}


@frappe.whitelist(methods=["GET", "POST"])
def get_bootstrap():
    if not (
        frappe.has_permission("Media Plan", "read")
        or frappe.has_permission("Media Plan", "create")
    ):
        frappe.throw(_("Not permitted to access Media Plan Wizard."), frappe.PermissionError)
    return {
        "can_create": frappe.has_permission("Media Plan", "create"),
        "user": frappe.session.user,
        "fields": {
            "planned_production": _ui_fields("Media Plan Production"),
            "planned_work_items": _ui_fields("Media Planned Work Item"),
            "risks": _ui_fields("Media Plan Risk"),
            "opportunities": _ui_fields("Media Plan Opportunity"),
        },
    }


@frappe.whitelist(methods=["GET", "POST"])
def get_plan(name: str):
    doc = frappe.get_doc("Media Plan", name)
    doc.check_permission("read")
    if not can_access_plan_owner(doc.get("plan_owner")):
        frappe.throw(_("This Media Plan is outside your reporting hierarchy."), frappe.PermissionError)
    main_meta = frappe.get_meta("Media Plan")
    result = {
        fieldname: doc.get(fieldname)
        for fieldname in MAIN_FIELDS
        if main_meta.get_field(fieldname) and _field_allowed(main_meta.get_field(fieldname), "read")
    }
    result["name"] = doc.name
    result["modified"] = str(doc.modified)
    result["docstatus"] = doc.docstatus
    result["workflow_state"] = doc.get("workflow_state")

    for table_fieldname, config in SOURCE_CONFIG.items():
        target_fields = _source_target_fields(config["doctype"])
        result[table_fieldname] = []
        for row in doc.get(table_fieldname) or []:
            row_data = _serialize_child_row(config["doctype"], row)
            goal_field = target_fields.get("goal")
            audience_field = target_fields.get("audience")
            row_data["goals"] = (
                [row.get(goal_field)] if goal_field and row.get(goal_field) else []
            )
            row_data["audiences"] = (
                [row.get(audience_field)] if audience_field and row.get(audience_field) else []
            )
            result[table_fieldname].append(row_data)

    result["risks"] = [_serialize_child_row("Media Plan Risk", row) for row in doc.get("risks") or []]
    result["opportunities"] = [
        _serialize_child_row("Media Plan Opportunity", row) for row in doc.get("opportunities") or []
    ]
    result["inferred_goals"] = [
        _serialize_child_row("Media Plan Goal", row) for row in doc.get("goals") or []
    ]
    result["goal_audience_distribution"] = [
        _serialize_child_row("Media Goal Audience", row)
        for row in doc.get("goal_audience_distribution") or []
    ]
    workflow_doc = {
        "doctype": doc.doctype,
        "name": doc.name,
        "docstatus": doc.docstatus,
        "workflow_state": doc.get("workflow_state"),
        "status": doc.get("status"),
        "owner": doc.owner,
        "modified": str(doc.modified),
    }
    for workflow_field in main_meta.fields:
        if (
            workflow_field.fieldname
            and workflow_field.fieldtype
            not in {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Table", "Table MultiSelect"}
            and _field_allowed(workflow_field, "read")
        ):
            workflow_doc[workflow_field.fieldname] = doc.get(workflow_field.fieldname)
    workflow_name = frappe.db.get_value(
        "Workflow",
        {"document_type": "Media Plan", "is_active": 1},
        "name",
    )
    workflow_state_field = (
        frappe.db.get_value("Workflow", workflow_name, "workflow_state_field")
        if workflow_name
        else None
    ) or "workflow_state"
    return {
        "doc": result,
        "can_write": bool(doc.has_permission("write") and doc.docstatus == 0),
        "workflow_doc": workflow_doc,
        "workflow_state_field": workflow_state_field,
    }


@frappe.whitelist(methods=["POST"])
def save_plan(payload, name: str | None = None, expected_modified: str | None = None):
    payload = _parse_payload(payload)
    _validate_basic(payload)

    if name:
        doc = frappe.get_doc("Media Plan", name)
        doc.check_permission("write")
        if not can_access_plan_owner(doc.get("plan_owner")):
            frappe.throw(_("This Media Plan is outside your reporting hierarchy."), frappe.PermissionError)
        if doc.docstatus != 0:
            frappe.throw(_("Only Draft Media Plans can be edited from the wizard."))
        if not expected_modified or str(doc.modified) != str(expected_modified):
            frappe.throw(
                _("This Media Plan was changed after you opened it. Reload the wizard before saving."),
                frappe.TimestampMismatchError,
            )
    else:
        if not frappe.has_permission("Media Plan", "create"):
            frappe.throw(_("Not permitted to create Media Plan."), frappe.PermissionError)
        doc = frappe.new_doc("Media Plan")

    requested_plan_owner = payload.get("plan_owner") or frappe.session.user
    if not can_access_plan_owner(requested_plan_owner):
        frappe.throw(_("The selected Plan Owner is outside your reporting hierarchy."), frappe.PermissionError)

    main_meta = frappe.get_meta("Media Plan")
    for fieldname in MAIN_FIELDS:
        df = main_meta.get_field(fieldname)
        if df and not df.read_only and _field_allowed(df, "write") and fieldname in payload:
            doc.set(fieldname, _clean_field_value(df, payload.get(fieldname)))

    if main_meta.has_field("status") and not doc.get("status"):
        doc.status = "Draft"

    start_date = getdate(payload.get("start_date"))
    end_date = getdate(payload.get("end_date"))
    source_pairs = []
    source_pair_seen = set()
    inferred_goals = []
    inferred_audiences = []

    for table_fieldname, config in SOURCE_CONFIG.items():
        target_fields = _source_target_fields(config["doctype"])
        doc.set(table_fieldname, [])
        rows = payload.get(table_fieldname) or []
        if not isinstance(rows, list):
            frappe.throw(_("{0} must be a list.").format(table_fieldname))
        _validate_row_limit(rows, MAX_SOURCE_ROWS_PER_TABLE, table_fieldname)
        for row in rows:
            if not isinstance(row, dict) or _row_is_empty(row, config["doctype"]):
                continue
            goal_field = target_fields.get("goal")
            audience_field = target_fields.get("audience")
            goals = _bounded_unique_strings(
                row.get("goals")
                or ([row.get(goal_field)] if goal_field and row.get(goal_field) else []),
                _("Media Goals"),
                MAX_GOALS_PER_SOURCE,
            )
            audiences = _bounded_unique_strings(
                row.get("audiences")
                or ([row.get(audience_field)] if audience_field and row.get(audience_field) else []),
                _("Target Audiences"),
                MAX_AUDIENCES_PER_SOURCE,
            )
            if goals:
                _validate_links("Media Goal", goals)
                if goal_field:
                    row[goal_field] = goals[0]
            if audiences:
                _validate_links("Target Audience", audiences)
                if audience_field:
                    row[audience_field] = audiences[0]

            clean = _clean_child_row(config["doctype"], row, "write")
            source_meta = frappe.get_meta(config["doctype"])
            if source_meta.has_field("planned_start_date"):
                clean["planned_start_date"] = clean.get("planned_start_date") or str(start_date)
            if source_meta.has_field("planned_end_date"):
                clean["planned_end_date"] = clean.get("planned_end_date") or str(end_date)
            _validate_source_dates(clean, start_date, end_date, source_meta)

            doc.append(table_fieldname, clean)
            for goal in goals:
                if goal not in inferred_goals:
                    inferred_goals.append(goal)
                for audience in audiences:
                    pair = (goal, audience)
                    if pair not in source_pair_seen:
                        if len(source_pairs) >= MAX_TARGETING_RELATIONS:
                            frappe.throw(_("Too many goal and target-audience relations in this plan."))
                        source_pair_seen.add(pair)
                        source_pairs.append(pair)
            for audience in audiences:
                if audience not in inferred_audiences:
                    inferred_audiences.append(audience)

    _replace_simple_table(doc, "risks", payload.get("risks") or [])
    _replace_simple_table(doc, "opportunities", payload.get("opportunities") or [])
    _replace_inferred_goals(doc, inferred_goals, payload.get("inferred_goals") or [])
    _replace_inferred_audiences(doc, inferred_audiences)
    _replace_distribution(doc, payload, inferred_goals, inferred_audiences, source_pairs)

    if doc.is_new():
        doc.insert()
    else:
        doc.save()

    return {
        "success": True,
        "name": doc.name,
        "modified": str(doc.modified),
        "route": "/app/media-plan-wizard?media_plan=" + doc.name,
        "form_route": "/app/media-plan/" + doc.name,
    }


def _ui_fields(doctype):
    fields = []
    for df in frappe.get_meta(doctype).fields:
        if (
            not df.fieldname
            or df.hidden
            or not _field_allowed(df, "read")
            or df.fieldtype
            in {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Table", "Table MultiSelect"}
        ):
            continue
        fields.append(
            {
                "fieldname": df.fieldname,
                "label": df.label,
                "fieldtype": df.fieldtype,
                "options": df.options,
                "reqd": df.reqd,
                "read_only": df.read_only,
                "default": df.default,
                "description": df.description,
                "depends_on": df.depends_on,
                "mandatory_depends_on": df.mandatory_depends_on,
                "read_only_depends_on": df.read_only_depends_on,
                "precision": df.precision,
                "length": df.length,
            }
        )
    return fields


def _parse_payload(payload):
    if isinstance(payload, str):
        if len(payload.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            frappe.throw(_("The Media Plan payload is too large."))
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            frappe.throw(_("Payload must contain valid JSON."))
    if not isinstance(payload, dict):
        frappe.throw(_("Payload must be a JSON object."))
    if len(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")) > MAX_PAYLOAD_BYTES:
        frappe.throw(_("The Media Plan payload is too large."))
    return payload


def _validate_basic(payload):
    for fieldname in ("plan_name", "project", "start_date", "end_date"):
        if not payload.get(fieldname):
            frappe.throw(_("Missing required field: {0}").format(fieldname))
    if getdate(payload.get("end_date")) < getdate(payload.get("start_date")):
        frappe.throw(_("End Date cannot be before Start Date."))
    _validate_link("Project", payload.get("project"))


def _clean_child_row(doctype, row, permission_type="write"):
    clean = {}
    meta = frappe.get_meta(doctype)
    for df in meta.fields:
        if (
            not df.fieldname
            or df.hidden
            or df.read_only
            or not _field_allowed(df, permission_type)
            or df.fieldtype
            in {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Table", "Table MultiSelect"}
        ):
            continue
        raw_value = row.get(df.fieldname)
        if raw_value in (None, ""):
            continue
        clean[df.fieldname] = _clean_field_value(df, raw_value)
    for df in meta.fields:
        if df.reqd and _field_allowed(df, permission_type) and clean.get(df.fieldname) in (None, ""):
            frappe.throw(_("Missing required field {0} in {1}.").format(df.label, doctype))
    return clean


def _row_is_empty(row, doctype):
    fields = {df.fieldname for df in frappe.get_meta(doctype).fields if df.fieldname}
    return not any(row.get(fieldname) not in (None, "") for fieldname in fields)


def _validate_source_dates(row, plan_start, plan_end, source_meta):
    has_start = source_meta.has_field("planned_start_date") and row.get("planned_start_date")
    has_end = source_meta.has_field("planned_end_date") and row.get("planned_end_date")
    row_start = getdate(row.get("planned_start_date")) if has_start else None
    row_end = getdate(row.get("planned_end_date")) if has_end else None
    if row_start and row_end and row_end < row_start:
        frappe.throw(_("Planned End Date cannot be before Planned Start Date."))
    if (row_start and (row_start < plan_start or row_start > plan_end)) or (
        row_end and (row_end < plan_start or row_end > plan_end)
    ):
        frappe.throw(_("Production and Work Item dates must be within the Media Plan period."))


def _replace_simple_table(doc, fieldname, rows):
    if not frappe.get_meta("Media Plan").has_field(fieldname):
        return
    doc.set(fieldname, [])
    table_df = frappe.get_meta("Media Plan").get_field(fieldname)
    if not isinstance(rows, list):
        frappe.throw(_("{0} must be a list.").format(fieldname))
    _validate_row_limit(rows, MAX_SIMPLE_ROWS_PER_TABLE, fieldname)
    for row in rows:
        if isinstance(row, dict) and not _row_is_empty(row, table_df.options):
            doc.append(fieldname, _clean_child_row(table_df.options, row))


def _replace_inferred_goals(doc, goals, submitted_rows):
    if not frappe.get_meta("Media Plan").has_field("goals"):
        return
    submitted_by_goal = {}
    if not isinstance(submitted_rows, list):
        frappe.throw(_("Inferred goals must be a list."))
    _validate_row_limit(submitted_rows, MAX_TARGETING_RELATIONS, "inferred_goals")
    for row in submitted_rows:
        if isinstance(row, dict):
            value = row.get("media_goal") or row.get("goal") or row.get("goal_title")
            if value:
                submitted_by_goal[value] = row
    doc.set("goals", [])
    meta = frappe.get_meta("Media Plan Goal")
    for goal in goals:
        row = {}
        if meta.has_field("media_goal"):
            row["media_goal"] = goal
        if meta.has_field("goal_title"):
            row["goal_title"] = _link_title("Media Goal", goal)
        if meta.has_field("goal_type"):
            row["goal_type"] = submitted_by_goal.get(goal, {}).get("goal_type") or "Short Term"
        if meta.has_field("priority") and submitted_by_goal.get(goal, {}).get("priority"):
            row["priority"] = submitted_by_goal[goal]["priority"]
        doc.append("goals", row)


def _replace_inferred_audiences(doc, audiences):
    if not frappe.get_meta("Media Plan").has_field("target_audiences"):
        return
    doc.set("target_audiences", [])
    meta = frappe.get_meta("Media Plan Target Audience")
    for audience in audiences:
        row = {"target_audience": audience}
        if meta.has_field("audience_name"):
            row["audience_name"] = _link_title("Target Audience", audience)
        doc.append("target_audiences", row)


def _replace_distribution(doc, payload, goals, audiences, source_pairs):
    if not frappe.get_meta("Media Plan").has_field("goal_audience_distribution"):
        return
    allowed_pairs = set(source_pairs)
    rows = payload.get("goal_audience_distribution") or []
    if not isinstance(rows, list):
        frappe.throw(_("Goal audience distribution must be a list."))
    _validate_row_limit(rows, MAX_TARGETING_RELATIONS, "goal_audience_distribution")
    seen = set()
    totals = {}
    has_percentage = set()
    percentage_counts = {}
    doc.set("goal_audience_distribution", [])
    for row in rows:
        if not isinstance(row, dict) or not cint(row.get("selected", 1)):
            continue
        goal = str(row.get("media_goal") or row.get("goal") or "").strip()
        audience = str(row.get("target_audience") or "").strip()
        if goal not in goals or audience not in audiences or (goal, audience) not in allowed_pairs:
            frappe.throw(_("The goal/audience distribution contains a relation not inferred from execution items."))
        if (goal, audience) in seen:
            frappe.throw(_("Duplicate goal/audience distribution row."))
        seen.add((goal, audience))
        percentage = row.get("allocation_percentage")
        clean = {
            "goal_reference": "goal::" + goal,
            "goal": goal,
            "target_audience": audience,
            "selected": 1,
        }
        if percentage not in (None, ""):
            percentage = flt(percentage)
            if percentage < 0 or percentage > 100:
                frappe.throw(_("Allocation Percentage must be between 0 and 100."))
            clean["allocation_percentage"] = percentage
            totals[goal] = totals.get(goal, 0) + percentage
            has_percentage.add(goal)
            percentage_counts[goal] = percentage_counts.get(goal, 0) + 1
        if row.get("priority"):
            clean["priority"] = row.get("priority")
        if row.get("notes"):
            clean["notes"] = row.get("notes")
        doc.append("goal_audience_distribution", clean)
    if seen != allowed_pairs:
        frappe.throw(_("Goal/audience distribution must include every relation inferred from execution items."))
    for goal in has_percentage:
        required_count = len([pair for pair in allowed_pairs if pair[0] == goal])
        if percentage_counts.get(goal, 0) != required_count:
            frappe.throw(_("Enter percentages for all audiences of {0}, or leave all percentages empty.").format(goal))
        if totals.get(goal, 0) < 99.99 or totals.get(goal, 0) > 100.01:
            frappe.throw(
                _("Audience allocation for {0} is {1}%. It must equal 100%.").format(goal, totals.get(goal, 0))
            )


def _validate_links(doctype, values):
    for value in values:
        _validate_link(doctype, value)


def _unique_strings(values):
    result = []
    for value in values:
        value = str(value or "").strip()
        if value and value not in result:
            result.append(value)
    return result


def _bounded_unique_strings(values, label, maximum):
    if not isinstance(values, list):
        frappe.throw(_("{0} must be a list.").format(label))
    if len(values) > maximum:
        frappe.throw(_("{0} exceeds the allowed limit of {1}.").format(label, maximum))
    return _unique_strings(values)


def _validate_row_limit(rows, maximum, label):
    if len(rows) > maximum:
        frappe.throw(_("{0} exceeds the allowed limit of {1} rows.").format(label, maximum))


def _clean_field_value(df, value):
    if isinstance(value, (dict, list, tuple, set)):
        frappe.throw(_("Invalid structured value for {0}.").format(df.label))
    if isinstance(value, str):
        value = value.strip()
        if len(value) > MAX_TEXT_VALUE_LENGTH:
            frappe.throw(_("Value is too long for {0}.").format(df.label))
    if value in (None, ""):
        return value
    if df.fieldtype == "Link":
        _validate_link(df.options, value)
    elif df.fieldtype == "Select":
        options = [option.strip() for option in (df.options or "").split("\n") if option.strip()]
        if options and value not in options:
            frappe.throw(_("Invalid value for {0}: {1}").format(df.label, value))
    elif df.fieldtype == "Int":
        value = cint(value)
    elif df.fieldtype in {"Float", "Currency", "Percent"}:
        value = flt(value)
    return value


def _validate_link(doctype, value):
    if not doctype or not value:
        frappe.throw(_("Invalid or inaccessible linked record."), frappe.PermissionError)
    exists = frappe.db.exists(doctype, value)
    permitted = bool(
        exists
        and (
            frappe.has_permission(doctype, "read", doc=value)
            or frappe.has_permission(doctype, "select", doc=value)
        )
    )
    if not permitted:
        frappe.throw(_("Invalid or inaccessible linked record."), frappe.PermissionError)


def _field_allowed(df, permission_type):
    permlevel = cint(df.permlevel or 0)
    if permlevel == 0:
        return True
    roles = set(frappe.get_roles())
    for permission in frappe.get_meta("Media Plan").permissions:
        if (
            cint(permission.permlevel or 0) == permlevel
            and permission.role in roles
            and cint(permission.get(permission_type) or 0)
        ):
            return True
    return False


def _serialize_child_row(doctype, row):
    result = {}
    for df in frappe.get_meta(doctype).fields:
        if (
            not df.fieldname
            or df.hidden
            or not _field_allowed(df, "read")
            or df.fieldtype
            in {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Table", "Table MultiSelect"}
        ):
            continue
        value = row.get(df.fieldname)
        if value is not None:
            result[df.fieldname] = value
    return result


def _source_target_fields(doctype):
    meta = frappe.get_meta(doctype)
    goal_field = _find_link_field(meta, "Media Goal")
    audience_field = _find_link_field(meta, "Target Audience")
    return {"goal": goal_field, "audience": audience_field}


def _find_link_field(meta, options):
    for df in meta.fields:
        if (
            df.fieldname
            and not df.hidden
            and df.fieldtype == "Link"
            and str(df.options or "").strip() == options
        ):
            return df.fieldname
    return None


def _link_title(doctype, name):
    _validate_link(doctype, name)
    title_field = frappe.get_meta(doctype).title_field
    return (frappe.db.get_value(doctype, name, title_field) or name) if title_field else name
