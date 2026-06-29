# Copyright (c) 2026, FOSS United and contributors
# For license information, please see license.txt

import json
import re
import secrets
import string

import frappe
import requests
from frappe import _
from frappe.utils import add_to_date, now_datetime


def _load_connection(lab_connection_name: str) -> tuple:
	"""Returns (url, api_key, api_secret) for a named LMS Lab Connection."""
	conn = frappe.get_doc("LMS Lab Connection", lab_connection_name)
	if not conn.is_active:
		frappe.throw(_("Lab connection '{0}' is not active.").format(lab_connection_name))

	api_secret = conn.get_password("api_secret")
	return conn.url.rstrip("/"), conn.api_key, api_secret


def _get_connection(lab_name: str) -> tuple:
	"""Returns (url, api_key, api_secret) for the lab's connection."""
	lab_connection_name = frappe.db.get_value("LMS Lab", lab_name, "lab_connection")
	if not lab_connection_name:
		frappe.throw(_("Lab has no connection configured."))
	return _load_connection(lab_connection_name)


def _raw_external_request(method: str, url: str, api_key: str, api_secret: str, **kwargs):
	"""Make an authenticated request to the external Frappe system. Lets connection errors propagate."""
	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
		"Expect": "",
	}
	if method.upper() != "GET":
		headers["Content-Type"] = "application/json"
	kwargs.setdefault("timeout", 30)
	return requests.request(method, url, headers=headers, **kwargs)


def _external_request(method: str, url: str, api_key: str, api_secret: str, **kwargs):
	"""Make an authenticated request to the external Frappe system, surfacing a friendly error on failure."""
	try:
		return _raw_external_request(method, url, api_key, api_secret, **kwargs)
	except requests.exceptions.RequestException:
		# DNS failure, connection refused, timeout, etc. — the external system
		# never produced an HTTP response at all.
		frappe.throw(_("Could not reach the lab system. Please wait a moment and try again."))


def validate_lab_roles(lab_doc) -> None:
	"""
	Checks every role configured on a Lab against the external system, so a typo
	is caught while configuring the lab rather than surfacing as an opaque
	user-creation failure once a student starts the session.
	"""
	role_names = sorted({r.role.strip() for r in (lab_doc.roles or []) if r.role and r.role.strip()})
	if not role_names or not lab_doc.lab_connection:
		return

	try:
		base_url, admin_key, admin_secret = _load_connection(lab_doc.lab_connection)
	except Exception:
		# Connection missing/inactive is already reported by the Lab Connection field itself.
		return

	try:
		resp = _raw_external_request(
			"GET",
			f"{base_url}/api/resource/Role",
			admin_key,
			admin_secret,
			params={
				"filters": json.dumps([["name", "in", role_names]]),
				"fields": json.dumps(["name"]),
				"limit": len(role_names),
			},
			timeout=10,
		)
	except requests.exceptions.RequestException:
		frappe.msgprint(
			_("Could not verify roles against the external system right now. Please double-check the role names manually."),
			indicator="orange",
			alert=True,
		)
		return

	if resp.status_code != 200:
		frappe.msgprint(
			_("Could not verify roles against the external system right now. Please double-check the role names manually."),
			indicator="orange",
			alert=True,
		)
		return

	found = {row["name"] for row in resp.json().get("data", [])}
	unknown = [r for r in role_names if r not in found]
	if unknown:
		frappe.throw(
			_("These roles do not exist on the external lab system: {0}").format(", ".join(unknown))
		)


def _external_error_detail(resp) -> str:
	"""
	Build a safe, human-readable detail for a failed external-system response.
	A genuine Frappe validation error comes back as JSON with `_server_messages`;
	anything else (an HTML error page from a crashed backend, a proxy's 502/503/504)
	means the lab system itself is unavailable, so its raw body is never shown to
	the student/instructor.
	"""
	try:
		data = resp.json()
		server_messages = json.loads(data.get("_server_messages") or "[]")
		if server_messages:
			message = json.loads(server_messages[0]).get("message")
			if message:
				return message
		if data.get("exception"):
			return str(data["exception"]).strip().splitlines()[-1]
	except (ValueError, TypeError, IndexError, KeyError):
		pass
	return _("the lab system is temporarily unavailable (HTTP {0})").format(resp.status_code)


def _slugify(text: str) -> str:
	text = text.lower()
	text = re.sub(r"[^a-z0-9]+", "_", text)
	return text.strip("_")[:20]


def _generate_password(length: int = 12) -> str:
	alphabet = string.ascii_letters + string.digits
	return "".join(secrets.choice(alphabet) for _ in range(length))


# ── Randomized session data ────────────────────────────────────────────────
# Pools used to build a unique, realistic data set for every lab session.
# Values are stored on the instance and substituted both into the on-screen
# instructions ({placeholder}) and into the evaluation criteria, so each
# student works with – and is graded against – their own random data.

_FIRST_NAMES = [
	"Jan", "Anna", "Piotr", "Katarzyna", "Tomasz", "Magdalena", "Marek",
	"Agnieszka", "Paweł", "Joanna", "Krzysztof", "Barbara", "Andrzej", "Ewa",
	"Michał", "Zofia", "Łukasz", "Natalia", "Grzegorz", "Aleksandra",
]
_LAST_NAMES = [
	"Kowalski", "Nowak", "Wiśniewski", "Wójcik", "Kowalczyk", "Kamiński",
	"Lewandowski", "Zieliński", "Szymański", "Woźniak", "Dąbrowski", "Kozłowski",
	"Jankowski", "Mazur", "Kwiatkowski", "Krawczyk", "Piotrowski", "Grabowski",
]
_COMPANY_CORES = [
	"Bałtyk", "Wisła", "Karpaty", "Mazury", "Tatry", "Odra", "Sudety",
	"Polonia", "Kontur", "Vertex", "Nordkom", "Stalprofil", "Agromax",
	"Technika", "Optimal", "Synteza", "Granit", "Horyzont", "Magnus", "Delta",
]
_COMPANY_SUFFIXES = ["Sp. z o.o.", "S.A.", "Sp. j.", "Sp. k.", "Sp. z o.o."]
_CITIES = [
	("Warszawa", "00-001"), ("Kraków", "30-001"), ("Gdańsk", "80-001"),
	("Wrocław", "50-001"), ("Poznań", "60-001"), ("Łódź", "90-001"),
	("Szczecin", "70-001"), ("Lublin", "20-001"), ("Katowice", "40-001"),
	("Bydgoszcz", "85-001"), ("Białystok", "15-001"), ("Rzeszów", "35-001"),
]
_STREETS = [
	"Kwiatowa", "Lipowa", "Słoneczna", "Polna", "Ogrodowa", "Leśna", "Krótka",
	"Akacjowa", "Brzozowa", "Sportowa", "Przemysłowa", "Handlowa", "Kolejowa",
]
_ITEM_CORES = [
	("Laptop", "biznesowy"), ("Monitor", "LED 27\""), ("Drukarka", "laserowa"),
	("Klawiatura", "mechaniczna"), ("Myszka", "bezprzewodowa"), ("Router", "Wi-Fi 6"),
	("Dysk SSD", "1 TB"), ("Tablet", "10 cali"), ("Smartfon", "5G"),
	("Słuchawki", "z mikrofonem"), ("Skaner", "dokumentów"), ("Projektor", "Full HD"),
]
_CUSTOMER_GROUPS = ["Commercial", "Individual", "Non Profit", "Government"]
_TERRITORIES = ["Rest Of The World", "Poland"]


def _rand_phone() -> str:
	return "+48 " + " ".join(
		"".join(secrets.choice(string.digits) for _ in range(3)) for _ in range(3)
	)


def _rand_nip() -> str:
	# 10 cyfr (uproszczony, bez walidacji sumy kontrolnej) — realistyczny format NIP
	return "".join(secrets.choice(string.digits) for _ in range(10))


def _generate_session_data(token: str) -> dict:
	"""
	Build a unique, internally-consistent set of random business data for one
	lab session. `token` is a short unique fragment (derived from the instance
	name / session id) appended to globally-unique fields (customer name, item
	code) so concurrent sessions never collide on the external system.
	"""
	first = secrets.choice(_FIRST_NAMES)
	last = secrets.choice(_LAST_NAMES)
	company_core = secrets.choice(_COMPANY_CORES)
	company_suffix = secrets.choice(_COMPANY_SUFFIXES)
	city, base_pin = secrets.choice(_CITIES)
	street = secrets.choice(_STREETS)
	street_no = secrets.randbelow(180) + 1
	pin = f"{secrets.randbelow(90) + 10}-{secrets.randbelow(900) + 100}"
	item_core, item_variant = secrets.choice(_ITEM_CORES)

	# Globally-unique business names get a short session token suffix.
	customer_company = f"{company_core} {company_suffix} [{token}]"
	contact_first = first
	contact_last = last
	email_domain = re.sub(r"[^a-z0-9]+", "", company_core.lower()) or "firma"
	contact_email = f"{first.lower()}.{re.sub(r'[^a-z]', '', last.lower())}@{email_domain}.pl"

	item_name = f"{item_core} {item_variant} {token}"
	item_code = f"{re.sub(r'[^A-Z0-9]', '', item_core.upper())[:6]}-{token}"
	unit_price = (secrets.randbelow(46) + 5) * 100 + secrets.choice([0, 50, 99])
	order_qty = secrets.randbelow(8) + 2
	discount_pct = secrets.choice([5, 8, 10, 12, 15])

	return {
		# Klient (firma)
		"customer_name": customer_company,
		"customer_type": "Company",
		"customer_group": secrets.choice(_CUSTOMER_GROUPS),
		"territory": secrets.choice(_TERRITORIES),
		"tax_id": _rand_nip(),
		# Kontakt / osoba
		"contact_first": contact_first,
		"contact_last": contact_last,
		"contact_full": f"{contact_first} {contact_last}",
		"contact_email": contact_email,
		"contact_phone": _rand_phone(),
		# Adres
		"addr_street": f"ul. {street} {street_no}",
		"addr_city": city,
		"addr_pincode": pin,
		# Produkt
		"item_name": item_name,
		"item_code": item_code,
		"item_group": "Products",
		"item_uom": "Nos",
		"item_price": str(unit_price),
		# Transakcja
		"order_qty": str(order_qty),
		"discount_pct": str(discount_pct),
		# Lead / CRM
		"lead_first": secrets.choice(_FIRST_NAMES),
		"lead_company": f"{secrets.choice(_COMPANY_CORES)} {secrets.choice(_COMPANY_SUFFIXES)} [{token}]",
	}


def _load_session_data(instance) -> dict:
	"""Return the parsed session_data dict for an instance (doc or row)."""
	raw = instance.get("session_data") if hasattr(instance, "get") else getattr(instance, "session_data", None)
	if not raw:
		return {}
	try:
		return json.loads(raw)
	except (ValueError, TypeError):
		return {}


def _build_substitutions(instance, session_data: dict = None) -> dict:
	"""
	Map of {placeholder} -> value used to render instructions and resolve
	evaluation filters / expected values. Combines the core instance fields
	with the randomized session data.
	"""
	if session_data is None:
		session_data = _load_session_data(instance)
	subs = {
		"company_name": instance.get("company_name") if hasattr(instance, "get") else instance.company_name,
		"username": instance.get("external_username") if hasattr(instance, "get") else instance.external_username,
	}
	subs.update(session_data)
	return {k: ("" if v is None else str(v)) for k, v in subs.items()}


def _apply_substitutions(text: str, subs: dict) -> str:
	"""Replace every {key} placeholder in text with its value from subs."""
	if not text:
		return text
	for key, value in subs.items():
		text = text.replace("{" + key + "}", value)
	return text


def _step_to_dict(s):
	"""Serialize a LMS Lab Step child row to a plain dict for the API response."""
	return {
		"title": s.title,
		"instructions": getattr(s, "instructions", None) or "",
		"item_type": getattr(s, "item_type", None) or "Step",
		"autocomplete_nav_path": getattr(s, "autocomplete_nav_path", None) or "",
		"autocomplete_nav_params": getattr(s, "autocomplete_nav_params", None) or "",
		"idx": s.idx,
	}


def _get_lab_doc(lab: str):
	"""
	Load LMS Lab document safely. If child tables for new doctypes (e.g. LMS Lab Role)
	don't exist yet in the database (before bench migrate), fetch steps separately.
	"""
	try:
		return frappe.get_doc("LMS Lab", lab)
	except Exception:
		# Fallback when tabLMS Lab Role table doesn't exist yet (pre-migration).
		# Build a minimal object with the fields we need.
		import types

		lab_data = frappe.db.get_value(
			"LMS Lab",
			lab,
			["title", "passing_percentage", "max_session_minutes", "company_prefix", "lab_connection"],
			as_dict=True,
		)
		if not lab_data:
			frappe.throw(_("Lab {0} not found").format(lab))

		steps_raw = frappe.db.sql(
			"SELECT * FROM `tabLMS Lab Step` WHERE parent=%s ORDER BY idx",
			lab,
			as_dict=True,
		)

		class _FakeLab:
			def get(self, key, default=None):
				return getattr(self, key, default)

		doc = _FakeLab()
		for k, v in lab_data.items():
			setattr(doc, k, v)
		doc.steps = [types.SimpleNamespace(**s) for s in steps_raw]
		doc.roles = []
		try:
			criteria_raw = frappe.db.sql(
				"SELECT * FROM `tabLMS Lab Evaluation Criterion` WHERE parent=%s ORDER BY idx",
				lab,
				as_dict=True,
			)
			doc.evaluation_criteria = [types.SimpleNamespace(**c) for c in criteria_raw]
		except Exception:
			doc.evaluation_criteria = []
		return doc


def provision_lab_instance(lab: str, course: str, lesson: str):
	"""
	Creates or returns an existing Active lab instance for the current user.
	Provisions a new Company + User on the external Frappe system if needed.
	"""
	member = frappe.session.user
	if member == "Guest":
		frappe.throw(_("Please login to start a lab."))

	# Auto-enroll the student if they don't have an enrollment record yet.
	if not frappe.db.exists("LMS Enrollment", {"course": course, "member": member}):
		try:
			frappe.get_doc({
				"doctype": "LMS Enrollment",
				"course": course,
				"member": member,
				"member_type": "Student",
			}).save(ignore_permissions=True)
		except Exception:
			pass

	# Return existing active instance if available
	existing = frappe.db.get_value(
		"LMS Lab Instance",
		{"lab": lab, "member": member, "status": ["in", ["Provisioning", "Active"]]},
		["name", "status", "company_name", "external_username", "expires_at", "current_step", "session_data"],
		as_dict=True,
	)
	if existing and existing.status == "Active":
		lab_doc = _get_lab_doc(lab)
		base_url, *__ = _get_connection(lab)
		ext_password = frappe.get_doc("LMS Lab Instance", existing.name, check_permission=False).get_password(
			"external_password"
		)
		return {
			"instance": existing.name,
			"lab_title": lab_doc.title,
			"url": base_url,
			"external_username": existing.external_username,
			"external_password": ext_password,
			"company_name": existing.company_name,
			"session_data": _load_session_data(existing),
			"expires_at": str(existing.expires_at),
			"current_step": existing.current_step,
			"steps": [_step_to_dict(s) for s in lab_doc.steps],
			"total_steps": len(lab_doc.steps),
		}

	# Block provisioning while a previous instance is still being cleaned up
	pending = frappe.db.get_value(
		"LMS Lab Instance",
		{"lab": lab, "member": member, "status": ["in", ["Evaluating", "Cleaning"]]},
		"status",
	)
	if pending:
		frappe.throw(
			_("Previous lab session is still being cleaned up. Please wait a moment and try again."),
			frappe.ValidationError,
		)

	lab_doc = _get_lab_doc(lab)
	base_url, admin_key, admin_secret = _get_connection(lab)

	# Clean up any Failed instances so their orphaned external resources get removed
	failed_instances = frappe.get_all(
		"LMS Lab Instance",
		filters={"lab": lab, "member": member, "status": "Failed"},
		pluck="name",
	)
	for fi in failed_instances:
		try:
			cleanup_lab_instance(fi, admin_key=admin_key, admin_secret=admin_secret, base_url=base_url)
		except Exception:
			pass

	ext_password = _generate_password(14)

	# Create the instance record first (Provisioning state) so its auto-generated
	# name can be used as the lab *session id*. The company and the login are then
	# derived from that session id — every session is fully isolated and the
	# external resources carry the session id, making them trivial to trace/clean.
	instance = frappe.get_doc(
		{
			"doctype": "LMS Lab Instance",
			"lab": lab,
			"member": member,
			"status": "Provisioning",
			"external_password": ext_password,
			"current_step": 1,
		}
	)
	instance.insert(ignore_permissions=True)

	session_id = instance.name
	# Short token used to keep globally-unique business fields collision-free.
	token = re.sub(r"[^A-Za-z0-9]", "", session_id)[-6:].upper()
	prefix = lab_doc.company_prefix or "LAB"
	company_name = f"{prefix}-{session_id}"
	company_abbr = re.sub(r"[^A-Za-z0-9]", "", session_id)[:5].upper()
	ext_username = f"lab-{session_id}@lab.local"
	session_data = _generate_session_data(token)

	frappe.db.set_value(
		"LMS Lab Instance",
		instance.name,
		{
			"company_name": company_name,
			"external_username": ext_username,
			"session_data": json.dumps(session_data, ensure_ascii=False),
		},
		update_modified=False,
	)
	instance.company_name = company_name
	instance.external_username = ext_username
	frappe.db.commit()

	try:
		# 1. Create Company on external system (409 = already exists from a prior attempt, OK)
		company_payload = {
			"company_name": company_name,
			"abbr": company_abbr,
			"country": "Poland",
			"default_currency": "PLN",
		}
		resp = _external_request(
			"POST",
			f"{base_url}/api/resource/Company",
			admin_key,
			admin_secret,
			json=company_payload,
		)
		if resp.status_code not in (200, 201, 409):
			frappe.throw(_("Failed to create company: {0}").format(_external_error_detail(resp)))

		# 2. Create User on external system; if already exists update password instead
		configured_roles = [{"role": r.role} for r in (getattr(lab_doc, "roles", None) or [])]
		member_language = frappe.db.get_value("User", member, "language") or "en"
		user_payload = {
			"email": ext_username,
			"first_name": member.split("@")[0].title(),
			"send_welcome_email": 0,
			"new_password": ext_password,
			"language": member_language,
			"roles": configured_roles or [{"role": "System Manager"}],
		}
		resp = _external_request(
			"POST",
			f"{base_url}/api/resource/User",
			admin_key,
			admin_secret,
			json=user_payload,
		)
		if resp.status_code == 409:
			# User already exists from a prior failed attempt — update password
			resp = _external_request(
				"PUT",
				f"{base_url}/api/resource/User/{ext_username}",
				admin_key,
				admin_secret,
				json={"new_password": ext_password},
			)
			if resp.status_code not in (200, 201):
				frappe.throw(_("Failed to update existing user: {0}").format(_external_error_detail(resp)))
		elif resp.status_code not in (200, 201):
			frappe.throw(_("Failed to create user: {0}").format(_external_error_detail(resp)))

		# 3. Restrict user to their lab company via User Permission
		# Without this the user sees all companies (incl. the main production company).
		user_perm_payload = {
			"user": ext_username,
			"allow": "Company",
			"for_value": company_name,
			"is_default": 1,
			"apply_to_all_doctypes": 1,
		}
		_external_request(
			"POST",
			f"{base_url}/api/resource/User Permission",
			admin_key,
			admin_secret,
			json=user_perm_payload,
		)

		# 5. Generate API keys for the new user
		resp = _external_request(
			"POST",
			f"{base_url}/api/method/frappe.core.doctype.user.user.generate_keys",
			admin_key,
			admin_secret,
			json={"user": ext_username},
		)
		ext_api_key = None
		ext_api_secret = None
		if resp.status_code == 200:
			msg = resp.json().get("message", {})
			ext_api_key = msg.get("api_key")
			ext_api_secret = msg.get("api_secret")

		# 6. Update instance to Active
		max_minutes = lab_doc.max_session_minutes or 60
		now = now_datetime()
		expires_at = add_to_date(now, minutes=max_minutes)
		frappe.db.set_value(
			"LMS Lab Instance",
			instance.name,
			{
				"status": "Active",
				"api_key": ext_api_key,
				"api_secret": ext_api_secret,
				"provisioned_at": now,
				"expires_at": expires_at,
			},
		)
		frappe.db.commit()

	except Exception as e:
		frappe.db.set_value(
			"LMS Lab Instance",
			instance.name,
			{
				"status": "Failed",
				"error_log": str(e),
			},
		)
		frappe.db.commit()
		raise

	return {
		"instance": instance.name,
		"lab_title": lab_doc.title,
		"url": base_url,
		"external_username": ext_username,
		"external_password": ext_password,
		"company_name": company_name,
		"session_data": session_data,
		"expires_at": str(expires_at),
		"current_step": 1,
		"steps": [_step_to_dict(s) for s in lab_doc.steps],
		"total_steps": len(lab_doc.steps),
	}


@frappe.whitelist()
def get_lab_cleanup_status(lab: str, include_active: bool = False):
	"""
	Returns whether retry should be blocked.
	include_active=True: also block while instance is still Active/Provisioning
	(used when polling after lab_ended — evaluate_lab may not have run yet).
	"""
	member = frappe.session.user
	if member == "Guest":
		return {"cleaning": False}
	statuses = (
		["Active", "Provisioning", "Evaluating", "Cleaning"] if include_active else ["Evaluating", "Cleaning"]
	)
	status = frappe.db.get_value(
		"LMS Lab Instance",
		{"lab": lab, "member": member, "status": ["in", statuses]},
		"status",
	)
	return {"cleaning": bool(status), "status": status or None}


@frappe.whitelist()
def get_lab_instance(lab: str):
	"""Returns active instance details for the current user or None."""
	member = frappe.session.user
	instance = frappe.db.get_value(
		"LMS Lab Instance",
		{"lab": lab, "member": member, "status": "Active"},
		["name", "company_name", "external_username", "expires_at", "current_step", "session_data"],
		as_dict=True,
	)
	if not instance:
		return None

	lab_doc = _get_lab_doc(lab)
	base_url, *__ = _get_connection(lab)
	ext_password = frappe.get_doc("LMS Lab Instance", instance.name, check_permission=False).get_password(
		"external_password"
	)
	return {
		"instance": instance.name,
		"lab_title": lab_doc.title,
		"url": base_url,
		"external_username": instance.external_username,
		"external_password": ext_password,
		"company_name": instance.company_name,
		"session_data": _load_session_data(instance),
		"expires_at": str(instance.expires_at),
		"current_step": instance.current_step,
		"steps": [_step_to_dict(s) for s in lab_doc.steps],
		"total_steps": len(lab_doc.steps),
	}


@frappe.whitelist()
def navigate_lab_step(lab_instance: str, direction: str = None, step: int = None):
	"""Move current_step forward/backward or jump to an absolute step number."""
	member = frappe.session.user
	instance = frappe.get_doc("LMS Lab Instance", lab_instance, check_permission=False)

	if instance.member != member:
		frappe.throw(_("Not authorized."))
	if instance.status != "Active":
		frappe.throw(_("Lab session is not active."))

	lab_doc = _get_lab_doc(instance.lab)
	total = len(lab_doc.steps)

	if step is not None:
		new_step = max(1, min(int(step), total))
	elif direction == "next":
		new_step = min(instance.current_step + 1, total)
	else:
		new_step = max(instance.current_step - 1, 1)

	frappe.db.set_value("LMS Lab Instance", lab_instance, "current_step", new_step, update_modified=False)
	return {"current_step": new_step, "total_steps": total}


@frappe.whitelist()
def enqueue_evaluate_lab(lab: str, lesson: str, course: str):
	"""
	Queues evaluate_lab as a background job so the browser window can close immediately.
	Looks up instance_name while the session is valid and passes it directly to the job,
	so the background worker does not need to resolve it via frappe.session.user
	(which would be 'Administrator' in an async worker context).
	"""
	member = frappe.session.user
	instance_name = frappe.db.get_value(
		"LMS Lab Instance",
		{"lab": lab, "member": member, "status": ["in", ["Active", "Evaluating"]]},
		"name",
	)
	if not instance_name:
		return {"queued": False, "reason": "no_active_session"}

	frappe.enqueue(
		"lms.lms.lab.evaluate_lab",
		queue="long",
		timeout=600,
		now=False,
		lab=lab,
		lesson=lesson,
		course=course,
		_instance_name=instance_name,
		_member=member,
	)
	return {"queued": True}


@frappe.whitelist()
def evaluate_lab(lab: str, lesson: str, course: str, _user: str = None,
                 _instance_name: str = None, _member: str = None):
	"""
	Runs evaluation against the external Frappe system.
	Creates LMS Lab Submission. Triggers cleanup. Marks lesson complete if passed.
	When called from enqueue_evaluate_lab, _instance_name and _member are passed directly
	to avoid relying on frappe.session.user inside the async worker.
	"""
	from lms.lms.doctype.course_lesson.course_lesson import save_progress

	member = _member or _user or frappe.session.user

	if _instance_name:
		instance_name = _instance_name
	else:
		instance_name = frappe.db.get_value(
			"LMS Lab Instance",
			{"lab": lab, "member": member, "status": ["in", ["Active", "Evaluating"]]},
			"name",
		)
		if not instance_name:
			frappe.throw(_("No active lab session found."))

	frappe.db.set_value("LMS Lab Instance", instance_name, "status", "Evaluating")
	frappe.db.commit()

	# Ensure cleanup always runs even if evaluation raises an exception.
	# Without this, an unhandled error leaves status stuck on "Evaluating" forever.
	try:
		return _run_evaluate_lab(
			lab=lab, lesson=lesson, course=course,
			member=member, instance_name=instance_name,
			save_progress=save_progress,
		)
	except Exception:
		try:
			cleanup_lab_instance(instance_name)
		except Exception:
			pass
		raise


def _run_evaluate_lab(lab, lesson, course, member, instance_name, save_progress):

	instance = frappe.get_doc("LMS Lab Instance", instance_name, check_permission=False)
	lab_doc = _get_lab_doc(lab)
	base_url, admin_key, admin_secret = _get_connection(lab)

	company_name = instance.company_name
	ext_username = instance.external_username
	subs = _build_substitutions(instance)

	results = []
	score = 0.0
	max_score = 0.0

	for criterion in lab_doc.evaluation_criteria:
		max_score += criterion.points
		passed = False
		details = ""

		try:
			filters_str = _apply_substitutions(criterion.filters or "[]", subs)
			filters = json.loads(filters_str)

			fields = ["name"]
			if criterion.field_to_check:
				fields.append(criterion.field_to_check)

			params = {"filters": json.dumps(filters), "fields": json.dumps(fields), "limit": 10}
			resp = _external_request(
				"GET",
				f"{base_url}/api/resource/{criterion.doctype_to_check}",
				admin_key,
				admin_secret,
				params=params,
			)

			if resp.status_code != 200:
				details = f"Could not connect to the lab system (HTTP {resp.status_code})."
			else:
				data = resp.json().get("data", [])
				op = criterion.comparison_operator or "Exists"
				doctype_label = criterion.doctype_to_check

				if op == "Exists":
					passed = len(data) > 0
					details = (
						""
						if passed
						else f"No {doctype_label} record matching the required criteria was found."
					)
				elif data and criterion.field_to_check:
					actual = str(data[0].get(criterion.field_to_check, ""))
					expected = _apply_substitutions(criterion.expected_value or "", subs)
					if op == "Equals":
						passed = actual == expected
						if not passed:
							# Numeric-aware comparison so e.g. "2" matches "2.0".
							try:
								passed = float(actual) == float(expected)
							except (ValueError, TypeError):
								passed = False
						if not passed:
							details = f"Expected '{expected}', but found '{actual}'."
					elif op == "Contains":
						passed = expected in actual
						if not passed:
							details = f"Expected the value to contain '{expected}', but got '{actual}'."
					elif op == "Greater Than":
						try:
							passed = float(actual) > float(expected)
						except ValueError:
							passed = actual > expected
						if not passed:
							details = f"Expected a value greater than {expected}, but got '{actual}'."
					elif op == "Less Than":
						try:
							passed = float(actual) < float(expected)
						except ValueError:
							passed = actual < expected
						if not passed:
							details = f"Expected a value less than {expected}, but got '{actual}'."
					if passed:
						details = ""
				else:
					details = f"No {doctype_label} record was found to check the required field."

		except Exception as e:
			details = f"An error occurred during evaluation: {str(e)}"

		if passed:
			score += criterion.points

		results.append(
			{
				"criterion_name": criterion.criterion_name,
				"doctype_checked": criterion.doctype_to_check,
				"points_earned": criterion.points if passed else 0,
				"max_points": criterion.points,
				"passed": 1 if passed else 0,
				"details": details,
			}
		)

	percentage = (score / max_score * 100) if max_score > 0 else 0
	status = "Pass" if percentage >= lab_doc.passing_percentage else "Fail"

	submission = frappe.get_doc(
		{
			"doctype": "LMS Lab Submission",
			"lab": lab,
			"member": member,
			"lesson": lesson,
			"course": course,
			"score": score,
			"max_score": max_score,
			"percentage": percentage,
			"passing_percentage": lab_doc.passing_percentage,
			"status": status,
			"submission_time": now_datetime(),
			"results": results,
		}
	)
	submission.insert(ignore_permissions=True)
	frappe.db.commit()

	# Cleanup environment regardless of pass/fail
	try:
		cleanup_lab_instance(instance_name, admin_key=admin_key, admin_secret=admin_secret, base_url=base_url)
	except Exception:
		pass

	# Mark lesson as complete if passed
	if status == "Pass":
		try:
			save_progress(lesson=lesson, course=course, member=member)
		except Exception:
			pass

	return {
		"score": score,
		"max_score": max_score,
		"percentage": percentage,
		"status": status,
		"passing_percentage": lab_doc.passing_percentage,
		"results": results,
		"submission": submission.name,
	}


@frappe.whitelist()
def cleanup_lab_instance(
	lab_instance: str, admin_key: str = None, admin_secret: str = None, base_url: str = None
):
	"""
	Deletes provisioned resources on the external system:
	all documents owned by the lab user, the user, and the company.
	"""
	instance = frappe.get_doc("LMS Lab Instance", lab_instance, check_permission=False)

	# Allow System Manager to clean any instance; student can only clean their own
	if frappe.session.user != "Administrator" and instance.member != frappe.session.user:
		if not frappe.has_permission("LMS Lab Instance", "write"):
			frappe.throw(_("Not authorized."))

	frappe.db.set_value("LMS Lab Instance", lab_instance, "status", "Cleaning")
	frappe.db.commit()

	if not base_url or not admin_key or not admin_secret:
		base_url, admin_key, admin_secret = _get_connection(instance.lab)

	ext_username = instance.external_username
	company_name = instance.company_name

	# DocTypes to clean up, ordered so children/transactions come before master data.
	# All filtered by owner = ext_username (the lab user created them).
	CLEANUP_DOCTYPES = [
		# Transactions (must go before linked master data)
		"Sales Invoice",
		"Purchase Invoice",
		"Sales Order",
		"Purchase Order",
		"Delivery Note",
		"Purchase Receipt",
		"Payment Entry",
		"Journal Entry",
		"Stock Entry",
		"Quotation",
		# CRM
		"Opportunity",
		"Lead",
		# Master data that may have Address/Contact links
		"Customer",
		"Supplier",
		"Item",
	]

	errors = []

	def _fetch_names_by_owner(doctype):
		params = {
			"filters": json.dumps([["owner", "=", ext_username]]),
			"fields": json.dumps(["name"]),
			"limit": 500,
		}
		resp = _external_request(
			"GET", f"{base_url}/api/resource/{doctype}", admin_key, admin_secret, params=params
		)
		if resp.status_code != 200:
			return []
		return [row["name"] for row in resp.json().get("data", [])]

	def _delete_doc(doctype, name):
		_external_request(
			"DELETE", f"{base_url}/api/resource/{doctype}/{name}", admin_key, admin_secret
		)

	# Delete Address and Contact records owned by the lab user first,
	# so that Customer/Supplier deletion won't be blocked by linked records.
	for link_doctype in ("Address", "Contact"):
		try:
			for name in _fetch_names_by_owner(link_doctype):
				try:
					_delete_doc(link_doctype, name)
				except Exception as e:
					errors.append(f"{link_doctype} {name}: {str(e)}")
		except Exception as e:
			errors.append(f"{link_doctype}: {str(e)}")

	for doctype in CLEANUP_DOCTYPES:
		try:
			for name in _fetch_names_by_owner(doctype):
				try:
					_delete_doc(doctype, name)
				except Exception as e:
					errors.append(f"{doctype} {name}: {str(e)}")
		except Exception as e:
			errors.append(f"{doctype}: {str(e)}")

	# Delete the user
	try:
		_external_request("DELETE", f"{base_url}/api/resource/User/{ext_username}", admin_key, admin_secret)
	except Exception as e:
		errors.append(f"User delete: {str(e)}")

	# Delete the company
	try:
		_external_request(
			"DELETE", f"{base_url}/api/resource/Company/{company_name}", admin_key, admin_secret
		)
	except Exception as e:
		errors.append(f"Company delete: {str(e)}")

	frappe.db.set_value(
		"LMS Lab Instance",
		lab_instance,
		{
			"status": "Cleaned",
			"error_log": "\n".join(errors) if errors else "",
		},
	)
	frappe.db.commit()

	return {"status": "Cleaned", "errors": errors}


def cleanup_expired_instances():
	"""Scheduled job: clean up lab instances that have passed their expiry time."""
	from frappe.utils import now_datetime

	expired = frappe.get_all(
		"LMS Lab Instance",
		filters={"status": ["in", ["Active", "Evaluating"]], "expires_at": ["<", now_datetime()]},
		fields=["name"],
	)
	for inst in expired:
		try:
			cleanup_lab_instance(inst.name)
		except Exception as e:
			frappe.log_error(f"Lab cleanup failed for {inst.name}: {str(e)}", "Lab Cleanup Error")
