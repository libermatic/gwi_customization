// Copyright (c) 2018, Libermatic and contributors
// For license information, please see license.txt

frappe.ui.form.on('Microfinance Loan Settings', {
  refresh: function(frm) {
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
    frm.fields_dict['write_off_account'].get_query = doc => ({
      filters: {
        root_type: 'Expense',
        is_group: false,
      },
    });
  },
});
