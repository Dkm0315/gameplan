# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GPSprint(Document):
	def validate(self):
		if self.start_date and self.end_date and self.start_date > self.end_date:
			frappe.throw("Sprint start date cannot be after end date")

