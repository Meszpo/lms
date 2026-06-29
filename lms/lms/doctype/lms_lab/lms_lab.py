# Copyright (c) 2026, FOSS United and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms.lab import ensure_role_isolation, validate_lab_roles


class LMSLab(Document):
	def validate(self):
		self.validate_duplicate_roles()
		validate_lab_roles(self)
		if self.has_role_changes():
			ensure_role_isolation(self)

	def validate_duplicate_roles(self):
		seen = set()
		for row in self.roles or []:
			role = (row.role or "").strip()
			if not role:
				continue
			if role in seen:
				frappe.throw(_("Role '{0}' is assigned more than once.").format(role))
			seen.add(role)

	def has_role_changes(self) -> bool:
		"""
		True when the configured roles differ from what's saved in the database (or this
		is a new lab) — used to skip re-running the external-system permission setup
		(dozens of REST calls) on every routine save, only doing it when it can actually
		matter.
		"""
		if self.is_new():
			return bool(self.roles)
		before = self.get_doc_before_save()
		old_roles = {r.role for r in (before.roles or [])} if before else set()
		new_roles = {r.role for r in (self.roles or [])}
		return old_roles != new_roles
