// Copyright (c) 2018, Libermatic and contributors
// For license information, please see license.txt

frappe.ui.form.on('Microfinance Loan', {
  refresh: async function(frm) {
    frm.trigger('clear_chart');
    if (frm.doc.docstatus === 1 && frm.doc.__onload['chart_data']) {
      frm.trigger('render_chart');
    }
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
      frm.page.add_menu_item(__('Account Statement'), function() {
        frappe.set_route('query-report', 'Microfinance Account Statement', {
          loan: frm.doc['name'],
        });
      });
      frm.page.add_menu_item(__('Update Principal / Recovery'), function() {
        frappe.prompt(
          [
            {
              fieldname: 'principal_amount',
              fieldtype: 'Currency',
              label: 'Principal',
              default: frm.doc['loan_principal'],
            },
            {
              fieldname: 'recovery_amount',
              fieldtype: 'Currency',
              label: 'Recovery',
              default: frm.doc['recovery_amount'],
            },
          ],
          async function(values) {
            await frappe.call({
              method: 'gwi_customization.microfinance.api.loan.update_amounts',
              args: { name: frm.doc['name'], ...values },
            });
            frm.reload_doc();
            frappe.show_alert('Amounts updated.', 5);
          },
          'Update Amounts',
          'Submit'
        );
      });
      frm.page.add_menu_item(__('Interest Tool'), function() {
        frappe.set_route('interest_tool', {
          loan: frm.doc['name'],
        });
      });
    }
  },
  render_chart: function(frm) {
    const chart_area = frm.$wrapper.find('.form-graph').removeClass('hidden');
    const chart = new frappeChart.Chart(chart_area[0], {
      type: 'percentage',
      data: frm.doc.__onload['chart_data'],
      colors: ['green', 'orange', 'blue', 'grey'],
    });
  },
  clear_chart: function(frm) {
    frm.$wrapper
      .find('.form-graph')
      .empty()
      .addClass('hidden');
  },
});
