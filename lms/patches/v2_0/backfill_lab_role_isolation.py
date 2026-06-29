import frappe

from lms.lms.lab import ensure_role_isolation


def execute():
	"""Apply owner-based role isolation to every existing lab.

	`ensure_role_isolation` (added alongside this patch) restricts each lab role's
	visibility on the external system to documents it owns, but `LMS Lab.validate()`
	only runs it when the roles table changes on save — so labs created before this
	feature existed, whose roles haven't been touched since, never got it applied.
	Without this, students using those labs see every other student's (and any
	pre-existing demo) customers/items/orders on the external system.
	"""
	labs = frappe.get_all("LMS Lab", filters={"lab_connection": ["is", "set"]}, pluck="name")
	for lab_name in labs:
		try:
			ensure_role_isolation(frappe.get_doc("LMS Lab", lab_name))
		except Exception:
			frappe.log_error(f"Lab role isolation backfill failed for {lab_name}", "Lab Isolation Patch")
