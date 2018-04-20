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
      frm.page.add_menu_item(__('Account Statement'), function(e) {
        frappe.set_route('query-report', 'Microfinance Account Statement', {
          loan: frm.doc['name'],
        });
      });
    }
  },
  onload: function(frm) {
    if (frm.doc.docstatus === 1) {
      frm.trigger('render_chart');
    }
  },
  render_chart: function(frm) {
    const chart_area = frm.$wrapper.find('.form-graph');
    chart_area.empty();
    const chart = new Chart({
      parent: chart_area[0],
      type: 'percentage',
      data: frm.doc.__onload['chart_data'],
      colors: ['green', 'orange', 'blue', 'grey'],
    });
    chart_area.removeClass('hidden');
    $(chart.container)
      .find('.title')
      .addClass('hidden');
    $(chart.container)
      .find('.sub-title')
      .addClass('hidden');
  },
});
