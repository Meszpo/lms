// Copyright (c) 2026, FOSS United and contributors
// For license information, please see license.txt

frappe.ui.form.on("LMS Lab Connection", {
	refresh: function (frm) {
		frm.add_custom_button(__("Test Connection"), function () {
			frm.call("test_connection");
		});
	},
});
