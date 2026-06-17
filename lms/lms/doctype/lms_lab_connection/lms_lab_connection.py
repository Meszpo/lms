# Copyright (c) 2026, FOSS United and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class LMSLabConnection(Document):
	@frappe.whitelist()
	def test_connection(self):
		api_secret = self.get_password("api_secret")
		_test_connection_request(self.url, self.api_key, api_secret)


@frappe.whitelist()
def test_connection_params(url, api_key, api_secret):
	_test_connection_request(url, api_key, api_secret)


def _test_connection_request(url, api_key, api_secret):
	import requests

	try:
		response = requests.get(
			f"{url.rstrip('/')}/api/method/frappe.auth.get_logged_user",
			headers={"Authorization": f"token {api_key}:{api_secret}"},
			timeout=10,
		)
		if response.status_code == 200:
			frappe.msgprint(_("Connection successful! Logged in as: {0}").format(response.json().get("message")))
		else:
			frappe.throw(_("Connection failed: {0}").format(response.text))
	except Exception as e:
		frappe.throw(_("Connection error: {0}").format(str(e)))
