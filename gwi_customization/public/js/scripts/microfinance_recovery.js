export default {
  refresh: function(frm) {
    frm.fields_dict['loan'].get_query = doc => ({
      filters: { docstatus: 1 },
    });
    frappe.ui.form.on('Microfinance Other Charge', {
      charge_amount: function(frm) {
        frm.trigger('calculate_totals');
      },
      charges_remove: function(frm) {
        frm.trigger('calculate_totals');
      },
    });
  },
  loan: function(frm) {
    frm.trigger('set_init_amounts');
  },
  posting_date: function(frm) {
    frm.trigger('set_init_amounts');
  },
  paid_amount: function(frm) {
    const { paid_amount } = frm.doc;
    if (paid_amount) {
      frm.call('allocate_amount');
    }
  },
  principal_amount: function(frm) {
    frm.trigger('calculate_totals');
  },
  total_interests: function(frm) {
    frm.trigger('calculate_totals');
  },
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
  set_init_amounts: async function(frm) {
    const { loan, posting_date } = frm.doc;
    if (loan && posting_date) {
      const { message } = await frappe.call({
        method: 'gwi_customization.microfinance.api.interest.get_init_amounts',
        args: { loan, posting_date },
      });
      Object.keys(message).forEach(field =>
        frm.set_value(field, message[field])
      );
    }
  },
  calculate_totals: function(frm) {
    if (
      frm.fields_dict['total_interests'] &&
      frm.fields_dict['total_charges']
    ) {
      const {
        total_interests = 0,
        principal_amount = 0,
        charges = [],
      } = frm.doc;
      const total_amount = total_interests + principal_amount;
      const total_charges = charges.reduce(
        (a, { charge_amount: x = 0 }) => a + x,
        0
      );
      frm.set_value('total_amount', total_interests + principal_amount);
      frm.set_value('total_charges', total_charges);
      frm.set_value('total_received', total_amount + total_charges);
    }
  },
};
