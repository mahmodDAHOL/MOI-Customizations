frappe.ui.form.on("Leave Application", {
	custom_hours: function (frm) {
		if (frm.doc.from_date && frm.doc.to_date && frm.doc.employee && frm.doc.leave_type) {
			// server call is done to include holidays in leave days calculations
			return frappe.call({
				method: "moi_app.custom.leave_application.get_number_of_leave_days",
				args: {
					employee: frm.doc.employee,
					leave_type: frm.doc.leave_type,
					from_date: frm.doc.from_date,
					to_date: frm.doc.to_date,
					half_day: frm.doc.half_day,
					half_day_date: frm.doc.half_day_date,
					half_day_hours: frm.doc.custom_hours
				},
				callback: function (r) {
					if (r && r.message) {
						console.log("dfdfdee"+r.message);
						frm.set_value("total_leave_days", r.message);
						frm.trigger("get_leave_balance");
					}
				},
			});
		}
	},
	leave_approver: function (frm) {
		if (frm.doc.leave_approver) {
			// Fetch the User document to get the linked employee
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "User",
					name: frm.doc.leave_approver
				},
				callback: function (r) {
					if (r.message && r.message.name) {
						// If user has linked employee, fetch the employee name
						frappe.call({
							method: "frappe.client.get",
							args: {
								doctype: "Employee",
								filters: {
									"user_id": r.message.name  // This field links Employee to User
								},
								fields: ["name", "employee_name"]
							},
							callback: function (emp_r) {
								console.log("r.message" + emp_r.message.employee_name)
								if (emp_r.message) {
									frm.set_value("leave_approver_name", emp_r.message.employee_name);
								} else {
									// Fallback to user full name if employee fetch fails
									frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
								}
							}
						});
					} else {
						// If no employee linked, use user's full name
						frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
					}
				}
			});
		} else {
			// Clear the field if leave_approver is empty
			frm.set_value("leave_approver_name", "");
		}
	},
})



