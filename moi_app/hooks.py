app_name = "moi_app"
app_title = "Moi App"
app_publisher = "admin"
app_description = "All apps"
app_email = "amal@moi.gov.sy"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "moi_app",
# 		"logo": "/assets/moi_app/logo.png",
# 		"title": "Moi App",
# 		"route": "/moi_app",
# 		"has_permission": "moi_app.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/moi_app/css/moi_app.css"
# app_include_js = "/assets/moi_app/js/moi_app.js"

# include js, css files in header of web template
# web_include_css = "/assets/moi_app/css/moi_app.css"
# web_include_js = "/assets/moi_app/js/moi_app.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "moi_app/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Leave Application" : "public/js/leave_application.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "moi_app/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment

jinja = {
    "methods": [
        "moi_app.utils.number_to_arabic_words",
        "moi_app.utils.get_hijri_date",
        "moi_app.utils.convert_table",
        # ... other methods
    ]
}
# Installation
# ------------

# before_install = "moi_app.install.before_install"
# after_install = "moi_app.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "moi_app.uninstall.before_uninstall"
# after_uninstall = "moi_app.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "moi_app.utils.before_app_install"
# after_app_install = "moi_app.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "moi_app.utils.before_app_uninstall"
# after_app_uninstall = "moi_app.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "moi_app.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "Asset": "moi_app.permissions.asset_query_condition",
    "Material Request": "moi_app.permissions.material_request_query_condition",
    "Employee": "moi_app.permissions.get_permission_query_conditions_for_employee",
    "Vehicle": "moi_app.permissions.vehicle_query_conditions",
    "Request for Machinery Maintenance": "moi_app.permissions.request_for_machinery_maintenance_query_conditions",
    "Request Car Wash": "moi_app.permissions.request_car_wash_query_conditions",
    "Request a vehicle reservation": "moi_app.permissions.request_a_vehicle_reservation_query_conditions",
    "Technical Committee Receiving Minutes": "moi_app.permissions.technical_committee_receiving_minutes_query_conditions",
    "Request for an Oil Change from the Central Garage": "moi_app.permissions.request_for_an_oil_change_from_the_central_garage_query_conditions",
    "Cleaning Company Performance Evaluation": "moi_app.permissions.cleaning_company_performance_evaluation_query_conditions",
    "Leave Application": "moi_app.permissions.leave_application_query_conditions",
    "Attendance Request": "moi_app.permissions.attendance_request_query_conditions",
}
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Leave Application": "moi_app.custom.leave_application.LeaveApplicationThai"
}
# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    # Optional: Cleanup during migration period (TEMPORARY)
    "User": {
        "on_update": "moi_app.custom_hooks.user_hooks.cleanup_employee_permissions_on_user_update"
    },
    "Asset": {
        "before_save": "moi_app.utils.generate_item_qr"
    },
    "Leave Application": {
        "on_submit": "moi_app.utils.attach_pdf"
    },
    # "Purchase Order": {
    #     "on_update": "moi_app.utils.attach_pdf"
    # },
    

}

# Scheduled Tasks
# ---------------

scheduler_events = {
    
    "cron": {
        "0 4 * * *": [
            "fingerprint.api.fetch_checkins.scheduled_fetch_checkins"
        ]
    }
# 	"all": [
# 		"moi_app.tasks.all"
# 	],
# 	"daily": [
# 		"moi_app.tasks.daily"
# 	],
	# "hourly": [
	# 	"fingerprint.api.fetch_checkins.scheduled_fetch_checkins"
	# ],
# 	"weekly": [
# 		"moi_app.tasks.weekly"
# 	],
# 	"monthly": [
# 		"moi_app.tasks.monthly"
# 	],
}

# Testing
# -------

# before_tests = "moi_app.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "moi_app.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "moi_app.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["moi_app.utils.before_request"]
# after_request = ["moi_app.utils.after_request"]

# Job Events
# ----------
# before_job = ["moi_app.utils.before_job"]
# after_job = ["moi_app.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"moi_app.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


# import frappe

# def get_moi_doctypes():
#     """Get all DocTypes belonging to the 'MOI' module (case-insensitive)."""
#     return [
#         d for d in frappe.get_all(
#             "DocType",
#             filters=[["module", "=", "MOI"]],
#             pluck="name"
#         )
#     ]

# def get_moi_reports():
#     """Get Reports linked to MOI doctypes or explicitly in MOI module."""
#     moi_doctypes = get_moi_doctypes()
#     # Reports can be in module, or reference MOI doctypes
#     return [
#         r for r in frappe.get_all(
#             "Report",
#             filters=[
#                 ["module", "=", "MOI"],
#                 ["ref_doctype", "in", moi_doctypes + [""]]
#             ],
#             or_filters=[
#                 ["module", "=", "MOI"],
#                 ["ref_doctype", "in", moi_doctypes]
#             ],
#             pluck="name"
#         )
#     ]

# # 🔑 MAIN FIXTURES — MOI APP ONLY
# fixtures = [
    
#     # ✅ DocTypes in MOI module
#     {
#         "doctype": "DocType",
#         "filters": [["module", "=", "MOI"]]
#     },

#     # ✅ Configurations WITH `module` field (v14+)
#     {
#         "doctype": "Property Setter",
#         "filters": [["module", "=", "MOI"]]
#     },
#     {
#         "doctype": "Client Script",  # Replaces "Client Script"
#         "filters": [["module", "=", "MOI"]]
#     },
#     {
#         "doctype": "Server Script",
#         "filters": [["module", "=", "MOI"]]
#     },
#     {
#         "doctype": "Custom Field",
#         "filters": [["module", "=", "MOI"]]
#     },

#     # ✅ Print Formats (filter by MOI doctypes + non-standard)
#     {
#         "doctype": "Print Format",
#         "filters": [
#              ["module", "=", "MOI"],
#             # ["standard", "=", "No"]
#         ]
#     },

#     # ✅ Workspaces — match by module (if set) OR content (doctype names)
#     {
#         "dt": "Workspace",
#         "filters": [
#             ["company", "=", "Ministry of Information"]
#         ]
#     },

#     # ✅ Workflows & States (linked via document_type)
#     {
#         "doctype": "Workflow",
#     },


#     # ✅ Reports (custom & query-based)
#     {
#         "doctype": "Report",
#         "filters": [ ["module", "=", "MOI"]]
#     },



#     # ✅ Website Pages & Themes (match by name/module)
#     {
#         "doctype": "Web Page",
#         "filters": [ ["module", "=", "MOI"]]
#     },
#     {
#         "doctype": "Page",
#         "filters": [ ["module", "=", "MOI"]]
#     },
#     {
#         "doctype": "Web Form",
#         "filters": [ ["module", "=", "MOI"]]
#     },
#     {
#         "doctype": "Website Theme",
#         "filters": [ ["module", "=", "MOI"]]
#     },

#     # ✅ Bonus: Add missing customizations commonly used in MOI:
    
#     # Custom Roles (if role name contains MOI)
#     {
#         "dt": "Role",
#     },
#     {
#         "dt": "Workflow State",
#     },

#     {
#         "dt": "Dashboard",
#         "filters": [ ["module", "=", "MOI"]]
#     },
#     {
#         "dt": "User Permission",
#     },

# ]

