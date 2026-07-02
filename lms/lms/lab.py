# Copyright (c) 2026, FOSS United and contributors
# For license information, please see license.txt

import json
import re
import secrets
import string
import unicodedata

import frappe
import requests
from frappe import _
from frappe.utils import add_to_date, now_datetime

# DocTypes a lab session creates data in. Shared by cleanup (delete everything a
# session touched) and role isolation (scope each role's visibility to documents it
# owns) so the two stay in sync — anything a session can create is both something we
# need to tear down afterwards and something other students shouldn't see.
SESSION_DOCTYPES = [
	"Address",
	"Contact",
	"Lead",
	"Opportunity",
	"Quotation",
	"Sales Order",
	"Sales Invoice",
	"Delivery Note",
	"Purchase Order",
	"Purchase Receipt",
	"Purchase Invoice",
	"Payment Entry",
	"Journal Entry",
	"Stock Entry",
	"Customer",
	"Supplier",
	"Item",
]

# Roles deliberately excluded from automatic owner-isolation: these are reserved for
# genuine administrators (e.g. the provisioning service account), not lab students, so
# restricting them to "only documents they own" would be both wrong and surprising.
ISOLATION_EXEMPT_ROLES = {"System Manager", "Administrator"}


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


@frappe.whitelist()
def get_external_roles(lab_connection: str) -> list:
	"""
	Returns every role name available on the external system for a given Lab
	Connection, so the lab editor frontend can offer autocomplete and flag
	unknown role names as the instructor types, instead of only finding out on save.
	"""
	if not frappe.has_permission("LMS Lab", "write"):
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	base_url, admin_key, admin_secret = _load_connection(lab_connection)
	resp = _raw_external_request(
		"GET",
		f"{base_url}/api/resource/Role",
		admin_key,
		admin_secret,
		params={"fields": json.dumps(["name"]), "limit_page_length": 0},
		timeout=10,
	)
	if resp.status_code != 200:
		frappe.throw(_("Could not fetch roles from the external system."))

	return sorted(row["name"] for row in resp.json().get("data", []))



def _ensure_owner_restricted(base_url, admin_key, admin_secret, role: str, doctype: str) -> bool:
	"""
	Restrict `role` to only its own documents on `doctype` (permlevel 0), via Frappe's
	own Role Permission Manager endpoint — NOT by POSTing a Custom DocPerm directly.
	That matters: the first time any doctype gets a Custom DocPerm row, Frappe stops
	falling back to standard DocPerm for *every* role on that doctype, not just the one
	being restricted. The permission_manager.update endpoint handles this correctly by
	copying every role's current standard permissions into Custom DocPerm first (via
	`setup_custom_perms`) if that doctype doesn't have any custom rows yet, so roles we
	never touch keep exactly the access they had. It's also safe to call repeatedly —
	it updates the existing override row instead of creating a duplicate.

	Returns True on success or when the role has no standard access to this doctype at
	all (nothing to restrict). False only when the external system couldn't be reached.
	"""
	meta_resp = _raw_external_request(
		"GET", f"{base_url}/api/resource/DocType/{doctype}", admin_key, admin_secret, timeout=30
	)
	if meta_resp.status_code != 200:
		return False

	perms = (meta_resp.json().get("data") or {}).get("permissions") or []
	has_standard_access = any(
		p.get("role") == role and (p.get("permlevel") or 0) == 0 for p in perms
	)
	if not has_standard_access:
		return True

	resp = _raw_external_request(
		"POST",
		f"{base_url}/api/method/frappe.core.page.permission_manager.permission_manager.update",
		admin_key,
		admin_secret,
		json={"doctype": doctype, "role": role, "permlevel": 0, "ptype": "if_owner", "value": "1"},
		timeout=30,
	)
	return resp.status_code == 200


def ensure_role_isolation(lab_doc) -> None:
	"""
	Restricts each role assigned to this lab's students so they only see documents
	they own across SESSION_DOCTYPES (Customer, Item, Address, Sales Order, ...) —
	otherwise every student sees every other student's (and any pre-existing demo)
	data on the external system, which defeats the point of a sandboxed lab session.
	Best-effort and non-blocking: failures here shouldn't stop a lab from being saved.
	"""
	if not lab_doc.lab_connection:
		return

	role_names = sorted({
		r.role.strip()
		for r in (lab_doc.roles or [])
		if r.role and r.role.strip() and r.role.strip() not in ISOLATION_EXEMPT_ROLES
	})
	if not role_names:
		return

	try:
		base_url, admin_key, admin_secret = _load_connection(lab_doc.lab_connection)
	except Exception:
		return

	failed = False
	for role in role_names:
		for doctype in SESSION_DOCTYPES:
			try:
				if not _ensure_owner_restricted(base_url, admin_key, admin_secret, role, doctype):
					failed = True
			except requests.exceptions.RequestException:
				failed = True

	if failed:
		frappe.msgprint(
			_(
				"Could not fully restrict role visibility on the external system. "
				"Some roles/doctypes may still show other students' documents — "
				"check the Role Permission Manager there manually."
			),
			indicator="orange",
			alert=True,
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

	# Email local part must be ASCII (SMTP validator in this stack
	# rejects Unicode characters, so we transliterate Polish diacritics first).
	def _ascii_email_local_part(value: str) -> str:
		value = (value or "").strip().lower()
		if not value:
			return ""

		# Polish-specific transliteration to keep letters (e.g. paweł -> pawel).
		translit = {
			"ą": "a",
			"ć": "c",
			"ę": "e",
			"ł": "l",
			"ń": "n",
			"ó": "o",
			"ś": "s",
			"ż": "z",
			"ź": "z",
			"ß": "ss",  # just in case
		}
		for src, dst in translit.items():
			value = value.replace(src, dst)

		# Generic fallback for any remaining diacritics.
		value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")

		# Keep only allowed local-part characters used by the generator.
		value = re.sub(r"[^a-z0-9]", "", value)
		return value

	contact_first_local = _ascii_email_local_part(first) or "contact"
	contact_last_local = _ascii_email_local_part(last) or "person"
	contact_email = f"{contact_first_local}.{contact_last_local}@{email_domain}.pl"

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

	lab_doc = _get_lab_doc(lab)
	max_attempts = lab_doc.max_attempts or 0
	if max_attempts > 0:
		used_attempts = frappe.db.count(
			"LMS Lab Submission", {"lab": lab, "lesson": lesson, "member": member}
		)
		if used_attempts >= max_attempts:
			frappe.throw(
				_("You have exceeded the maximum number of attempts ({0}) for this lab").format(
					max_attempts
				),
				frappe.ValidationError,
			)

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

	base_url, admin_key, admin_secret = _get_connection(lab)

	# Clean up any Failed instances so their orphaned external resources get removed.
	# Enqueued rather than run inline: cleanup now walks the external system's link graph
	# and retries deletes across multiple passes, which is too slow to do inside the
	# student's "start lab" request — and isn't needed for it to succeed anyway, since
	# every new instance gets its own unique company/username regardless.
	failed_instances = frappe.get_all(
		"LMS Lab Instance",
		filters={"lab": lab, "member": member, "status": "Failed"},
		pluck="name",
	)
	for fi in failed_instances:
		frappe.enqueue(
			"lms.lms.lab.cleanup_lab_instance",
			queue="long",
			timeout=600,
			now=False,
			lab_instance=fi,
			admin_key=admin_key,
			admin_secret=admin_secret,
			base_url=base_url,
		)

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
				details = _("Could not connect to the lab system (HTTP {0}).").format(resp.status_code)
			else:
				data = resp.json().get("data", [])
				op = criterion.comparison_operator or "Exists"
				doctype_label = criterion.doctype_to_check

				if op == "Exists":
					passed = len(data) > 0
					details = (
						""
						if passed
						else _("No {0} record matching the required criteria was found.").format(doctype_label)
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
							details = _("Expected '{0}', but found '{1}'.").format(expected, actual)
					elif op == "Contains":
						passed = expected in actual
						if not passed:
							details = _("Expected the value to contain '{0}', but got '{1}'.").format(
								expected, actual
							)
					elif op == "Greater Than":
						try:
							passed = float(actual) > float(expected)
						except ValueError:
							passed = actual > expected
						if not passed:
							details = _("Expected a value greater than {0}, but got '{1}'.").format(
								expected, actual
							)
					elif op == "Less Than":
						try:
							passed = float(actual) < float(expected)
						except ValueError:
							passed = actual < expected
						if not passed:
							details = _("Expected a value less than {0}, but got '{1}'.").format(
								expected, actual
							)
					if passed:
						details = ""
				else:
					details = _("No {0} record was found to check the required field.").format(doctype_label)

		except Exception as e:
			details = _("An error occurred during evaluation: {0}").format(str(e))

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

	try:
		frappe.publish_realtime(
			event="lab_evaluated",
			message={"lab": lab, "lesson": lesson, "submission": submission.name},
			user=member,
		)
	except Exception:
		pass

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

	try:
		result = _do_cleanup(lab_instance, instance, base_url, admin_key, admin_secret)
	except Exception as e:
		# Without this, anything that interrupts cleanup mid-run (a timed-out request, a
		# worker getting killed, ...) leaves the instance stuck on "Cleaning" forever —
		# provision_lab_instance only ever retries instances marked "Failed".
		frappe.db.set_value(
			"LMS Lab Instance", lab_instance, {"status": "Failed", "error_log": str(e)}
		)
		frappe.db.commit()
		_notify_cleanup_failure(instance, str(e))
		raise

	if result.get("errors"):
		# The student can't act on this — only someone with access to the external
		# system can — so they're never shown it; course staff get notified instead.
		_notify_cleanup_failure(instance, "\n".join(result["errors"]))
	return result


def _notify_cleanup_failure(instance, error: str) -> None:
	"""Lets course staff know a lab session's data on the external system couldn't be
	fully removed, since the student has no way to act on it themselves."""
	from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
	from frappe.utils.user import get_users_with_role

	try:
		users = get_users_with_role("Course Creator")
		if not users:
			return
		notification = frappe._dict({
			"subject": _("Could not fully clean up lab data for {0} on the external system.").format(
				instance.member
			),
			"email_content": frappe.utils.escape_html(error)[:1000],
			"document_type": "LMS Lab Instance",
			"document_name": instance.name,
			"type": "Alert",
		})
		make_notification_logs(notification, users)
	except Exception:
		# Best-effort — a failed notification shouldn't mask the original cleanup error.
		pass


def _do_cleanup(lab_instance: str, instance, base_url: str, admin_key: str, admin_secret: str) -> dict:
	ext_username = instance.external_username
	company_name = instance.company_name

	# DocTypes known to be owned directly by the lab user. This is just the seed set —
	# _expand_linked() below walks the actual link graph from the user/company so
	# anything missing from this list (GL Entry, Stock Ledger Entry, a doctype added by
	# some other app, ...) still gets found, instead of being silently left behind.

	# DocTypes that must never be swept up and deleted even if the link graph somehow
	# points through them — structural/system metadata, not lab session data.
	DOCTYPE_DELETE_BLOCKLIST = {
		"DocType", "Role", "Module Def", "Custom Field", "Property Setter",
		"Workspace", "Print Format", "Report", "Page", "Client Script",
		"Server Script", "Webhook", "User", "Company",
	}

	errors = []

	def _fetch_names_by_filter(doctype, field, value):
		resp = _raw_external_request(
			"GET",
			f"{base_url}/api/resource/{doctype}",
			admin_key,
			admin_secret,
			params={
				"filters": json.dumps([[field, "=", value]]),
				"fields": json.dumps(["name"]),
				"limit_page_length": 0,
			},
			timeout=30,
		)
		if resp.status_code != 200:
			return []
		return [row["name"] for row in resp.json().get("data", [])]

	def _cancel_doc(doctype, name):
		"""Best-effort cancel so a submitted document can actually be deleted afterwards."""
		try:
			_raw_external_request(
				"POST",
				f"{base_url}/api/method/frappe.client.cancel",
				admin_key,
				admin_secret,
				json={"doctype": doctype, "name": name},
				timeout=30,
			)
		except requests.exceptions.RequestException:
			pass

	def _delete_doc(doctype, name) -> bool:
		try:
			resp = _raw_external_request(
				"DELETE", f"{base_url}/api/resource/{doctype}/{name}", admin_key, admin_secret, timeout=30
			)
		except requests.exceptions.RequestException:
			return False
		return resp.status_code in (200, 202)

	def _discover_linked(doctype, name):
		"""
		Everything that references (doctype, name). Safe to delete unconditionally:
		the seed is always a unique session identifier (this instance's username/company,
		or a document owned by it), so a Link field pointing at that exact value can only
		belong to this lab session — never shared master/lookup data.
		"""
		try:
			resp = _raw_external_request(
				"GET",
				f"{base_url}/api/method/frappe.desk.form.linked_with.get",
				admin_key,
				admin_secret,
				params={"doctype": doctype, "docname": name},
				timeout=30,
			)
		except requests.exceptions.RequestException:
			return []
		if resp.status_code != 200:
			return []
		data = (resp.json() or {}).get("message") or {}
		out = []
		for linked_doctype, info in data.items():
			if linked_doctype in DOCTYPE_DELETE_BLOCKLIST:
				continue
			for row in info.get("docs", []) or []:
				if row.get("name"):
					out.append((linked_doctype, row["name"]))
		return out

	def _expand_linked(todo: set, seeds: list, max_depth: int = 2):
		"""BFS outward from `seeds`, adding everything linked to them — and everything
		linked to those — up to `max_depth` hops. Mutates `todo` in place. `seeds` are
		used as BFS starting points even if already present in `todo` — that's the point
		when seeding from "every document found so far" to also reach second-degree links."""
		frontier = list(dict.fromkeys(seeds))
		seen = set(todo) | set(frontier)
		for _hop in range(max_depth):
			next_frontier = []
			for doctype, name in frontier:
				for pair in _discover_linked(doctype, name):
					if pair not in seen:
						seen.add(pair)
						todo.add(pair)
						next_frontier.append(pair)
			frontier = next_frontier
			if not frontier:
				break

	def _drain(todo: set, max_passes: int = 8):
		"""
		Repeatedly try to cancel+delete every (doctype, name) in `todo`. Each pass clears
		whatever is no longer blocked by a link to something deleted in a previous pass,
		so this self-resolves dependency ordering instead of relying on a hand-curated
		doctype order. Whatever is still stuck after `max_passes` is reported as an error.
		"""
		remaining = set(todo)
		for _pass in range(max_passes):
			if not remaining:
				break
			progressed = False
			for doctype, name in list(remaining):
				_cancel_doc(doctype, name)
				if _delete_doc(doctype, name):
					remaining.discard((doctype, name))
					progressed = True
			if not progressed:
				break
		for doctype, name in remaining:
			errors.append(f"{doctype} {name}: still linked/blocked after {max_passes} cleanup passes")

	# 1. Seed the to-delete set from documents directly owned by the lab user...
	todo = set()
	for doctype in SESSION_DOCTYPES:
		try:
			for name in _fetch_names_by_filter(doctype, "owner", ext_username):
				todo.add((doctype, name))
		except Exception as e:
			errors.append(f"{doctype}: {str(e)}")

	# ...plus anything keyed by `user` rather than `owner` (e.g. the User Permission
	# created during provisioning is owned by the admin account, not the lab user).
	try:
		for name in _fetch_names_by_filter("User Permission", "user", ext_username):
			todo.add(("User Permission", name))
	except Exception as e:
		errors.append(f"User Permission: {str(e)}")

	# 2. Walk the link graph from the company and from every document found so far —
	# catches GL Entry/Stock Ledger Entry/etc. and anything not in CLEANUP_DOCTYPES.
	_expand_linked(todo, [("Company", company_name), *todo])

	# 3. Cancel+delete everything found, retrying until nothing more can be cleared.
	_drain(todo)

	# 4. Delete the company — by now its own dependents (Account, Cost Center,
	# Warehouse, ...) should be gone too, either via step 3 or via Company's own
	# on_trash cleanup, which only runs once no GL Entry/Stock Ledger Entry remains.
	# Routed through _drain (not a single _delete_doc call) so a transient failure on
	# the external system gets retried instead of being reported as permanently stuck.
	_drain({("Company", company_name)})

	# 5. Delete the user — walk its link graph too (ToDo, assignments, and other core
	# housekeeping records aren't owned by the user, they just point at it) and drain
	# that before the final delete.
	user_todo = set()
	_expand_linked(user_todo, [("User", ext_username)])
	user_todo.add(("User", ext_username))
	_drain(user_todo)

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
