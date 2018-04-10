// Copyright (c) 2018, Libermatic and contributors
// For license information, please see license.txt

frappe.ui.form.on('Microfinance Loan', {
  refresh: async function(frm) {
    frm.fields_dict['loan_account'].get_query = doc => ({
      filters: {
        root_type: 'Asset',
        is_group: false,
      },
    });
    frm.fields_dict['interest_income_account'].get_query = doc => ({
      filters: {
        root_type: 'Income',
        is_group: false,
      },
    });
    if (frm.doc.__islocal) {
      frm.set_df_property('loan_account', 'reqd', 1);
      frm.set_df_property('interest_income_account', 'reqd', 1);
      const { message: settings } = await frappe.db.get_value(
        'Microfinance Loan Settings',
        null,
        ['loan_account', 'interest_income_account']
      );
      if (settings) {
        const { loan_account, interest_income_account } = settings;
        frm.set_value('loan_account', loan_account);
        frm.set_value('interest_income_account', interest_income_account);
      }
    }
    if (frm.doc.docstatus > 0) {
      frm.set_df_property('loan_principal', 'read_only', 1);
      frm.set_df_property('recovery_amount', 'read_only', 1);
    }
  },
});
