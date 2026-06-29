# Copyright (c) 2026, FOSS United and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms.lab import validate_lab_roles


class LMSLab(Document):
	def validate(self):
		self.validate_duplicate_roles()
		validate_lab_roles(self)

	def validate_duplicate_roles(self):
		seen = set()
		for row in self.roles or []:
			role = (row.role or "").strip()
			if not role:
				continue
			if role in seen:
				frappe.throw(_("Role '{0}' is assigned more than once.").format(role))
			seen.add(role)
