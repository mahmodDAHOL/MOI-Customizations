frappe.pages["moi-user-profile"].on_page_load = function (wrapper) {
    frappe.ui.make_app_page({
        parent: wrapper,
        title: __("MOI User Profile"),
        single_column: true
    });

    load_moi_user_profile_assets(wrapper);
};

function load_moi_user_profile_assets(wrapper) {
    frappe.require(
        "/assets/press_affairs_app/css/moi_user_profile.css",
        function () {
            load_moi_user_profile_data(wrapper);
        }
    );
}

function load_moi_user_profile_data(wrapper) {
    $(wrapper).find(".layout-main-section").html(`
        <div class="moi-empty-state">${__("Loading profile...")}</div>
    `);

    frappe.call({
        method: "press_affairs_app.moi.page.moi_user_profile.moi_user_profile.get_profile_data",
        freeze: false,
        callback: function (r) {
            const data = sanitize_profile_data(r.message || {});

            render_moi_user_profile(wrapper, data);
            bind_moi_user_profile_events(wrapper);
            render_energy_line_chart(wrapper, data.chart_data);
            load_attendance_compliance(wrapper, data.employee);
        },
        error: function () {
            $(wrapper).find(".layout-main-section").html(`
                <div class="moi-empty-state">${__("Unable to load profile data")}</div>
            `);
        }
    });
}

function load_attendance_compliance(wrapper, employee) {
    if (!employee) {
        render_attendance_compliance(wrapper, get_empty_attendance());
        return;
    }

    frappe.call({
        method: "advanced_timesheet_api",
        args: get_attendance_api_args(employee),
        freeze: false,
        callback: function (r) {
            const attendance = sanitize_attendance_data(r.message || {});
            render_attendance_compliance(wrapper, attendance);
        },
        error: function () {
            render_attendance_compliance(wrapper, get_empty_attendance());
        }
    });
}

function get_attendance_api_args(employee) {
    return {
        from_date: frappe.datetime.month_start(),
        to_date: frappe.datetime.get_today(),
        employee: employee
    };
}

function get_empty_attendance() {
    return {
        attendance_compliance: 0,
        expected_hours: "-",
        actual_hours: "-",
        unjustified_hours: "-",
        late_entry_hours: "-",
        exceptions_count: 0,
        leave_days: "-"
    };
}

function render_moi_user_profile(wrapper, data) {
    $(wrapper).find(".layout-main-section").empty();

    const html = frappe.render_template("moi_user_profile", data);
    const content = $(html);

    $(wrapper).find(".layout-main-section").append(content);
}

function render_energy_line_chart(wrapper, chartData) {
    const chartWrapper = $(wrapper).find(".moi-chart-container")[0];

    if (!chartWrapper) {
        return;
    }

    chartWrapper.innerHTML = "";

    if (!Array.isArray(chartData) || !chartData.length) {
        chartWrapper.innerHTML = `
            <div class="moi-empty-state">
                ${__("No chart data available")}
            </div>
        `;
        return;
    }

    const labels = chartData.map(function (row) {
        return row.date;
    });

    const values = chartData.map(function (row) {
        return safe_number(row.points);
    });

    new frappe.Chart(chartWrapper, {
        title: "",
        data: {
            labels: labels,
            datasets: [
                {
                    name: __("Energy Points"),
                    values: values
                }
            ]
        },
        type: "line",
        height: 260,
        colors: ["#44427B"],
        lineOptions: {
            hideDots: 0,
            heatline: 0,
            regionFill: 0
        },
        axisOptions: {
            xAxisMode: "tick",
            yAxisMode: "tick",
            xIsSeries: 1
        },
        tooltipOptions: {
            formatTooltipX: function (d) {
                return d;
            },
            formatTooltipY: function (d) {
                return d + " " + __("Points");
            }
        }
    });
}

function render_attendance_compliance(wrapper, attendance) {
    const page = $(wrapper).find(".moi-profile-page");

    page.find(".moi-performance-label").text(__("Attendance Compliance"));
    page.find(".moi-performance-subtitle").text(
        __("Work attendance commitment for current month")
    );

    page.find(".moi-performance-badge").text(`${attendance.attendance_compliance}%`);
    page.find(".moi-performance-value").text(`${attendance.attendance_compliance}%`);

    page.find(".moi-performance-progress-bar").css(
        "width",
        `${attendance.attendance_compliance}%`
    );

    page.find(".moi-performance-item").eq(0).find(".moi-performance-item-value")
        .text(attendance.expected_hours);

    page.find(".moi-performance-item").eq(1).find(".moi-performance-item-value")
        .text(attendance.actual_hours);

    page.find(".moi-performance-item").eq(2).find(".moi-performance-item-value")
        .text(attendance.unjustified_hours);

    page.find(".moi-performance-item").eq(3).find(".moi-performance-item-value")
        .text(attendance.late_entry_hours);

    page.find(".moi-performance-item").eq(4).find(".moi-performance-item-value")
        .text(attendance.exceptions_count);

    page.find(".moi-performance-item").eq(5).find(".moi-performance-item-value")
        .text(attendance.leave_days);
}

function bind_moi_user_profile_events(wrapper) {
    $(wrapper).find(".moi-edit-profile-btn").off("click").on("click", function () {
        frappe.set_route("Form", "User", frappe.session.user);
    });

    $(wrapper).find(".moi-user-settings-btn").off("click").on("click", function () {
        frappe.set_route("user-settings");
    });

    $(wrapper).find(".moi-leaderboard-btn").off("click").on("click", function () {
        frappe.set_route("leaderboard", "User");
    });

    $(wrapper).find(".moi-view-all-btn").off("click").on("click", function () {
        frappe.set_route("List", "Energy Point Log");
    });

    $(wrapper).find(".moi-task-open-btn").off("click").on("click", function () {
        const doctype = $(this).data("doctype");
        const docname = $(this).data("docname");

        if (doctype && docname) {
            frappe.set_route("Form", doctype, docname);
        }
    });

    $(wrapper).find(".moi-view-all-tasks-btn").off("click").on("click", function () {
        frappe.set_route("List", "ToDo", {
            allocated_to: frappe.session.user
        });
    });
}

function sanitize_profile_data(data) {
    const labels = data.labels || {};
    const leave_summary = data.leave_summary || {};

    return {
        direction: sanitize_direction(data.direction),
        lang: safe_text(data.lang || frappe.boot.lang || "en"),

        user: safe_text(data.user),
        employee: safe_text(data.employee),
        full_name: safe_text(data.full_name),
        user_image: safe_url(data.user_image || "/assets/frappe/images/ui/avatar.png"),

        ministry: safe_text(data.ministry),
        department: safe_text(data.department),
        designation: safe_text(data.designation),

        energy_points: safe_number(data.energy_points),
        monthly_points: safe_number(data.monthly_points),
        rank: safe_number(data.rank),
        monthly_rank: safe_number(data.monthly_rank),
        pending_leaves: safe_number(data.pending_leaves),

        attendance_compliance: safe_number(data.attendance_compliance),
        expected_hours: safe_text(data.expected_hours || "-"),
        actual_hours: safe_text(data.actual_hours || "-"),
        unjustified_hours: safe_text(data.unjustified_hours || "-"),
        late_entry_hours: safe_text(data.late_entry_hours || "-"),
        exceptions_count: safe_number(data.exceptions_count),
        leave_days: safe_text(data.leave_days || "-"),

        leave_summary: {
            approved: safe_number(leave_summary.approved),
            pending: safe_number(leave_summary.pending),
            rejected: safe_number(leave_summary.rejected)
        },

        leave_balances: sanitize_leave_balances(data.leave_balances || []),

        chart_data: sanitize_chart_data(data.chart_data || []),
        recent_activity: sanitize_activity_data(data.recent_activity || []),
        tasks: sanitize_tasks_data(data.tasks || []),

        labels: sanitize_labels(labels)
    };
}

function sanitize_attendance_data(message) {
    const summary = message.summary || message || {};

    const operational = summary.operational || {};
    const control = summary.control || {};
    const exceptions = summary.exceptions || {};

    return {
        attendance_compliance: clamp_number(
            control.compliance_rate,
            0,
            100
        ),

        expected_hours: safe_text(
            operational.total_expected_hours_display || "-"
        ),

        actual_hours: safe_text(
            operational.total_actual_work_hours_display || "-"
        ),

        unjustified_hours: safe_text(
            control.total_unjustified_hours_display || "-"
        ),

        late_entry_hours: safe_text(
            operational.total_late_entry_hours_display || "-"
        ),

        exceptions_count: safe_number(
            exceptions.total_employee_exception_requests || 0
        ),

        leave_days: safe_text(
            operational.total_leave_hours_display || "0m"
        )
    };
}

function sanitize_labels(labels) {
    const defaults = {
        active_employee: __("Active Employee"),
        edit_profile: __("Edit Profile"),
        user_settings: __("User Settings"),
        leaderboard: __("Leaderboard"),

        energy_points: __("Energy Points"),
        rank: __("Rank"),
        monthly_rank: __("Monthly Rank"),
        pending_leaves: __("Pending Leaves"),

        this_month: __("This Month"),
        overall_rank: __("Overall Rank"),

        attendance_compliance: __("Attendance Compliance"),
        expected_hours: __("Expected Hours"),
        actual_hours: __("Actual + Leave"),
        unjustified_hours: __("Unjustified"),
        late_entry_hours: __("Late Entry"),
        exceptions: __("Exceptions"),
        leave_days: __("Leave Days"),

        leave_summary: __("Leave Summary"),
        approved: __("Approved"),
        pending: __("Pending"),
        rejected: __("Rejected"),

        leave_balances: __("Leave Balances"),
        leave_balances_subtitle: __("Allocated and available leave balances"),
        leave_type: __("Leave Type"),
        total_allocated: __("Allocated"),
        used_leaves: __("Used"),
        pending_approval: __("Pending Approval"),
        available_leaves: __("Remaining"),
        no_leave_balances: __("No leave balances available"),

        recent_activity: __("Recent Activity"),
        activity_subtitle: __("Recent activity related to points and leave requests"),

        chart_title: __("Energy Points"),
        chart_subtitle: __("Energy points during last days"),

        daily: __("Daily"),
        weekly: __("Weekly"),
        monthly: __("Monthly"),

        my_tasks: __("My Tasks"),
        tasks_subtitle: __("Assigned tasks and expected closure dates"),
        task_status: __("Status"),
        task_due: __("Expected Closure"),
        task_priority: __("Priority"),
        view_task: __("Open"),
        no_tasks: __("No tasks assigned"),

        view_all: __("View All"),
        no_activity: __("No activity to show"),
        no_chart_data: __("No points data during the last 30 days")
    };

    Object.keys(defaults).forEach(function (key) {
        defaults[key] = safe_text(labels[key] || defaults[key]);
    });

    return defaults;
}

function sanitize_chart_data(rows) {
    if (!Array.isArray(rows)) {
        return [];
    }

    return rows.slice(0, 31).map(function (row) {
        return {
            date: safe_text(row.date),
            points: safe_number(row.points)
        };
    });
}

function sanitize_leave_balances(rows) {
    if (!Array.isArray(rows)) {
        return [];
    }

    return rows.slice(0, 30).map(function (row) {
        return {
            leave_type: safe_text(row.leave_type),
            total_allocated: safe_text(row.total_allocated),
            used_leaves: safe_text(row.used_leaves),
            pending_leaves: safe_text(row.pending_leaves),
            available_leaves: safe_text(row.available_leaves)
        };
    });
}

function sanitize_activity_data(rows) {
    if (!Array.isArray(rows)) {
        return [];
    }

    return rows.slice(0, 6).map(function (row) {
        return {
            title: safe_text(row.title),
            time: safe_text(row.time),
            points: safe_text(row.points),
            reference_doctype: safe_text(row.reference_doctype),
            reference_name: safe_text(row.reference_name)
        };
    });
}

function sanitize_tasks_data(rows) {
    if (!Array.isArray(rows)) {
        return [];
    }

    return rows.slice(0, 8).map(function (row) {
        return {
            name: safe_text(row.name),
            title: safe_text(row.title || row.description || __("Task")),
            status: safe_text(row.status || __("Open")),
            priority: safe_text(row.priority || __("Medium")),
            due_date: safe_text(row.due_date || row.date || "-"),
            expected_closure: safe_text(row.expected_closure || row.due_date || row.date || "-"),
            reference_type: safe_text(row.reference_type || row.reference_doctype),
            reference_name: safe_text(row.reference_name),
            is_overdue: Boolean(row.is_overdue),
            status_class: safe_css_class(row.status_class || get_task_status_class(row.status)),
            priority_class: safe_css_class(row.priority_class || get_task_priority_class(row.priority))
        };
    });
}

function get_task_status_class(status) {
    const value = String(status || "").toLowerCase();

    if (value.includes("open") || value.includes("pending")) {
        return "moi-task-status-open";
    }

    if (value.includes("closed") || value.includes("completed")) {
        return "moi-task-status-closed";
    }

    if (value.includes("cancelled")) {
        return "moi-task-status-cancelled";
    }

    return "moi-task-status-open";
}

function get_task_priority_class(priority) {
    const value = String(priority || "").toLowerCase();

    if (value.includes("high")) {
        return "moi-task-priority-high";
    }

    if (value.includes("low")) {
        return "moi-task-priority-low";
    }

    return "moi-task-priority-medium";
}

function sanitize_direction(direction) {
    return direction === "rtl" ? "rtl" : "ltr";
}

function safe_text(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function safe_number(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return 0;
    }

    return Math.round(number * 1000) / 1000;
}

function clamp_number(value, min, max) {
    const number = safe_number(value);
    return Math.min(Math.max(number, min), max);
}

function safe_url(value) {
    const url = String(value || "");

    if (
        url.startsWith("/assets/") ||
        url.startsWith("/files/") ||
        url.startsWith("/private/files/")
    ) {
        return safe_text(url);
    }

    return "/assets/frappe/images/ui/avatar.png";
}

function safe_css_class(value) {
    const text = String(value || "");

    if (/^[a-zA-Z0-9_-]+$/.test(text)) {
        return text;
    }

    return "";
}