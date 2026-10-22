# Copyright (c) 2026, FOSS United and contributors
# For license information, please see license.txt

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms.lab import (
	RESERVED_SESSION_PLACEHOLDERS,
	_fetch_external_doctype_fields,
	_load_connection,
	ensure_role_isolation,
	validate_lab_roles,
)

# Matches {label} and {label.fieldname} placeholder syntax.
_PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?\}")
_LABEL_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Fieldtypes that must arrive as a real JSON number/bool, never a quoted string. A
# {placeholder} always substitutes to a string (see _apply_substitutions in lab.py), so
# these fields must always be given as a literal JSON number — even a placeholder here
# would still break at provisioning time once substituted.
_NUMERIC_FIELDTYPES = {"Int", "Float", "Currency", "Percent", "Check"}
# Standard Frappe meta fields that aren't in meta.fields but still carry a strict type.
_STANDARD_FIELD_TYPES = {"docstatus": "Int", "idx": "Int"}


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

		connection = None
		if self.lab_connection:
			try:
				connection = _load_connection(self.lab_connection)
			except Exception:
				connection = None  # unreachable/misconfigured connection — skip type checks, not Seed Record editing
		meta_cache = {}

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

			if connection and row.target_doctype:
				type_errors = []
				_validate_field_types(row.target_doctype, parsed_values, type_errors, *connection, meta_cache)
				if type_errors:
					frappe.throw(
						_("Seed record '{0}': {1}").format(label, "<br>".join(type_errors)),
						title=_("Field type mismatch"),
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


def _validate_field_types(doctype, values, errors, base_url, admin_key, admin_secret, meta_cache, path=""):
	"""
	Recursively checks a parsed Field Values dict against the external system's DocType
	metadata: Int/Float/Currency/Percent/Check fields must be real JSON numbers/booleans,
	never quoted strings — a {placeholder} always substitutes to a string (see
	_apply_substitutions in lab.py), so even a templated value would break the same way
	once substituted. This is exactly the class of bug that silently produces a
	`TypeError: '<=' not supported between instances of 'str' and 'int'` deep inside the
	external system's own validation, long after Seed Records were saved here.
	Recurses into Table / Table MultiSelect child rows using the child DocType's fields.
	Best-effort: an unreachable/unknown doctype is skipped rather than blocking the save.
	"""
	if doctype not in meta_cache:
		meta_cache[doctype] = _fetch_external_doctype_fields(
			base_url, admin_key, admin_secret, doctype, include_table_fields=True
		)
	fields = meta_cache[doctype]
	if fields is None:
		return
	fields_by_name = {f["fieldname"]: f for f in fields}

	for fieldname, value in values.items():
		field = fields_by_name.get(fieldname)
		fieldtype = field["fieldtype"] if field else _STANDARD_FIELD_TYPES.get(fieldname)
		if not fieldtype:
			continue

		if fieldtype in _NUMERIC_FIELDTYPES:
			if isinstance(value, bool) or isinstance(value, (int, float)):
				continue
			if isinstance(value, str):
				errors.append(
					_(
						"field '{0}' is a {1} field but got the quoted text \"{2}\" instead of a "
						"plain JSON number — write {0}: {2} (no quotes), not {0}: \"{2}\"."
					).format(f"{path}{fieldname}", fieldtype, value)
				)
			else:
				errors.append(
					_("field '{0}' is a {1} field but got {2}.").format(
						f"{path}{fieldname}", fieldtype, type(value).__name__
					)
				)
		elif fieldtype in ("Table", "Table MultiSelect") and field and field.get("options"):
			if isinstance(value, list):
				for i, child_row in enumerate(value):
					if isinstance(child_row, dict):
						_validate_field_types(
							field["options"],
							child_row,
							errors,
							base_url,
							admin_key,
							admin_secret,
							meta_cache,
							path=f"{path}{fieldname}[{i}].",
						)
