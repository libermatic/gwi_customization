// Copyright (c) 2019, Libermatic and contributors
// For license information, please see license.txt

frappe.ui.form.on('Audit Statement', gwi.scripts.audit_statement);
frappe.ui.form.on(
  'Audit Statement Detail',
  gwi.scripts.audit_statement.audit_statement_detail
);
