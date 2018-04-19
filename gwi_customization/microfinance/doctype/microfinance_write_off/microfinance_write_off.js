// Copyright (c) 2018, Libermatic and contributors
// For license information, please see license.txt

async function set_current_outstanding(frm) {
  const { loan, posting_date } = frm.doc;
  if (loan && posting_date) {
    const { message: outstanding } = await frappe.call({
      method:
        'gwi_customization.microfinance.api.loan.get_outstanding_principal',
      args: {
        loan: frm.doc['loan'],
        posting_date: frm.doc['posting_date'],
      },
    });
    frm.set_value('current_outstanding', outstanding);
    frm.set_value('amount', null);
    frm.set_value('next_outstanding', null);
  }
}

frappe.ui.form.on('Microfinance Write Off', {
  refresh: function(frm) {},
  loan: set_current_outstanding,
  posting_date: set_current_outstanding,
  amount: function(frm) {
    const { amount, current_outstanding } = frm.doc;
    if (amount) {
      frm.set_value('next_outstanding', current_outstanding - amount);
    }
  },
});
