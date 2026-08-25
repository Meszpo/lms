# Copyright (c) 2026, FOSS United and contributors
# For license information, please see license.txt

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms.lab import RESERVED_SESSION_PLACEHOLDERS, ensure_role_isolation, validate_lab_roles

# Matches {label} and {label.fieldname} placeholder syntax.
_PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?\}")
_LABEL_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class LMSLab(Document):
	def validate(self):
		self.validate_duplicate_roles()
		self.validate_seed_records()
		validate_lab_roles(self)
		if self.has_role_changes() or self.has_seed_doctype_changes():
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

	def validate_seed_records(self):
		seen_labels = set()
		for row in self.seed_records or []:
			label = (row.label or "").strip()
			if not label:
				continue
			if label in RESERVED_SESSION_PLACEHOLDERS or label in seen_labels:
				frappe.throw(_("Seed record label '{0}' is used more than once.").format(label))
			if not _LABEL_RE.match(label):
				frappe.throw(
					_(
						"Seed record label '{0}' must contain only letters, numbers and "
						"underscores (no dots or spaces) — it's used as {{label}} and "
						"{{label.fieldname}} inside {{placeholder}} syntax."
					).format(label)
				)
			seen_labels.add(label)

			try:
				parsed_values = json.loads(row.field_values or "{}")
			except (ValueError, TypeError):
				frappe.throw(_("Seed record '{0}': Field Values is not valid JSON.").format(label))
			if not isinstance(parsed_values, dict):
				frappe.throw(_("Seed record '{0}': Field Values must be a JSON object.").format(label))

			if not _PLACEHOLDER_RE.search(row.field_values or ""):
				frappe.throw(
					_(
						"Seed record '{0}': Field Values must reference at least one "
						"{{placeholder}} (e.g. {{customer_name}}) — otherwise two students "
						"running this lab at the same time would create identical records "
						"on the external system."
					).format(label)
				)

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

	def has_seed_doctype_changes(self) -> bool:
		"""True when Seed Record target DocTypes changed, so a new target still gets role-isolated."""
		if self.is_new():
			return bool(self.seed_records)
		before = self.get_doc_before_save()
		old_doctypes = {r.target_doctype for r in (before.seed_records or [])} if before else set()
		new_doctypes = {r.target_doctype for r in (self.seed_records or [])}
		return old_doctypes != new_doctypes
