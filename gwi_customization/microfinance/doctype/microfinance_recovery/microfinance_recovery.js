// Copyright (c) 2018, Libermatic and contributors
// For license information, please see license.txt

function calculate_recovery_totals(frm) {
  if (frm.fields_dict['total_interests'] && frm.fields_dict['total_charges']) {
    const { total_amount = 0, principal_amount = 0, charges = [] } = frm.doc;
    frm.set_value('total_interests', total_amount - principal_amount);
    frm.set_value(
      'total_charges',
      charges.reduce((a, { charge_amount: x = 0 }) => a + x, 0)
    );
  }
}

async function set_recovery_amounts(frm) {
  const { loan, posting_date } = frm.doc;
  if (loan && posting_date) {
    const [
      { message: interest_amount = 0 },
      { message: { recovery_amount = 0 } = {} },
    ] = await Promise.all([
      frappe.call({
        method:
          'gwi_customization.microfinance.api.interest.get_current_interest',
        args: { loan, posting_date },
      }),
      frappe.db.get_value('Microfinance Loan', loan, 'recovery_amount'),
    ]);
    frm.set_value('total_amount', interest_amount + recovery_amount);
    frm.set_value('principal_amount', recovery_amount);
  }
}

frappe.ui.form.on('Microfinance Recovery', {
  refresh: function(frm) {
    frm.fields_dict['loan'].get_query = doc => ({
      filters: { docstatus: 1 },
    });
    frappe.ui.form.on('Microfinance Other Charge', {
      charge_amount: calculate_recovery_totals,
      charges_remove: calculate_recovery_totals,
    });
  },
  loan: set_recovery_amounts,
  posting_date: set_recovery_amounts,
  total_amount: calculate_recovery_totals,
  principal_amount: calculate_recovery_totals,
  mode_of_payment: async function(frm) {
    const { mode_of_payment, company } = frm.doc;
    frm.toggle_reqd(['cheque_no', 'cheque_date'], mode_of_payment == 'Cheque');
    const { message } = await frappe.call({
      method:
        'erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account',
      args: { mode_of_payment, company },
    });
    if (message) {
      frm.set_value('payment_account', message.account);
    }
  },
});
