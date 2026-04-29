import datetime
import frappe
from frappe import _
from frappe.utils import getdate, date_diff, cint, flt
from hrms.hr.doctype.leave_application.leave_application import (
	LeaveApplication,
	get_holidays,
	get_leave_entries,
	is_lwp,
	get_leave_balance_on
)
from hrms.hr.doctype.leave_application.leave_application import get_holidays
from hrms.hr.doctype.leave_application.leave_application import get_leave_entries


class LeaveApplicationThai(LeaveApplication):

	def validate_half_day_hours(self):
		if not self.half_day:
			self.custom_hours = None
		else:
			if not self.custom_hours:
				self.custom_hours = "4"

	# Overwrite
	def validate_balance_leaves(self):
		# Patch
		self.validate_half_day_hours()
		half_day_hours = self.custom_hours and float(self.custom_hours) or None
		# --
		if self.from_date and self.to_date:
			self.total_leave_days = get_number_of_leave_days(
				self.employee,
				self.leave_type,
				self.from_date,
				self.to_date,
				self.half_day,
				self.half_day_date,
				half_day_hours=half_day_hours  # Patch
			)
			

			if self.total_leave_days <= 0:
				frappe.throw(
					_(
						"The day(s) on which you are applying for leave are holidays. You need not apply for leave."
					)
				)

			if not is_lwp(self.leave_type):
				leave_balance = get_leave_balance_on(
					self.employee,
					self.leave_type,
					self.from_date,
					self.to_date,
					consider_all_leaves_in_the_allocation_period=True,
					for_consumption=True,
				)
				self.leave_balance = leave_balance.get("leave_balance")
				leave_balance_for_consumption = leave_balance.get("leave_balance_for_consumption")

				if self.status != "Rejected" and (
					leave_balance_for_consumption < self.total_leave_days or not leave_balance_for_consumption
				):
					self.show_insufficient_balance_message(leave_balance_for_consumption)


@frappe.whitelist()
def get_number_of_leave_days(
	employee: str,
	leave_type: str,
	from_date: datetime.date,
	to_date: datetime.date,
	half_day: int | str | None = None,
	half_day_date: datetime.date | str | None = None,
	holiday_list: str | None = None,
	half_day_hours: float | str | None = None,  # Allow string input
) -> float:
	"""Returns number of leave days between 2 dates after considering half day and holidays"""
	
	# --- Convert half_day_hours to float safely ---
	half_day_hours_value = 0.0
	if half_day_hours is not None:
		try:
			half_day_hours_value = float(half_day_hours)
		except (ValueError, TypeError):
			half_day_hours_value = 4.0  # Default to 4 hours if conversion fails
	else:
		half_day_hours_value = 4.0  # Default half day = 4 hours
	
	# --- Calculate number of days ---
	number_of_days = 0
	
	if cint(half_day) == 1:
		if getdate(from_date) == getdate(to_date):
			# Same day half leave
			number_of_days = half_day_hours_value / 8.0
			
		elif half_day_date and getdate(from_date) <= getdate(half_day_date) <= getdate(to_date):
			# Half day within the leave period
			number_of_days = date_diff(to_date, from_date) + (half_day_hours_value / 8.0)
		else:
			# Half day not properly specified - treat as full day
			number_of_days = date_diff(to_date, from_date) + 1
	else:
		# Full day leave
		number_of_days = date_diff(to_date, from_date) + 1
	
	# --- Subtract holidays if needed ---
	if not frappe.db.get_value("Leave Type", leave_type, "include_holiday"):
		holiday_days = get_holidays(employee, from_date, to_date, holiday_list=holiday_list)
		number_of_days = flt(number_of_days) - flt(holiday_days)
	
	return flt(number_of_days)

def get_leaves_for_period(
	employee: str,
	leave_type: str,
	from_date: datetime.date,
	to_date: datetime.date,
	skip_expired_leaves: bool = True,
) -> float:
	leave_entries = get_leave_entries(employee, leave_type, from_date, to_date)
	leave_days = 0

	for leave_entry in leave_entries:
		inclusive_period = leave_entry.from_date >= getdate(from_date) and leave_entry.to_date <= getdate(
			to_date
		)

		if inclusive_period and leave_entry.transaction_type == "Leave Encashment":
			leave_days += leave_entry.leaves

		elif (
			inclusive_period
			and leave_entry.transaction_type == "Leave Allocation"
			and leave_entry.is_expired
			and not skip_expired_leaves
		):
			leave_days += leave_entry.leaves

		elif leave_entry.transaction_type == "Leave Application":
			if leave_entry.from_date < getdate(from_date):
				leave_entry.from_date = from_date
			if leave_entry.to_date > getdate(to_date):
				leave_entry.to_date = to_date

			half_day = 0
			half_day_date = None
			# fetch half day date for leaves with half days
			if leave_entry.leaves % 1:
				half_day = 1
				half_day_date = frappe.db.get_value(
					"Leave Application", leave_entry.transaction_name, "half_day_date"
				)

			# Monkey Patch, get half day hours
			half_days_hours = -leave_entry.leaves % 1 * 8
			# --
			leave_days += (
				get_number_of_leave_days(
					employee,
					leave_type,
					leave_entry.from_date,
					leave_entry.to_date,
					half_day,
					half_day_date,
					holiday_list=leave_entry.holiday_list,
					# Monkey Patch, convert to half day hours
					half_day_hours=half_days_hours,
					# --
				)
				* -1
			)

	return leave_days
