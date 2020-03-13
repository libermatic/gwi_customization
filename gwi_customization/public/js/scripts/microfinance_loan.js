function calculate_recovery(frm) {
  const { loan_type, loan_principal = 0, emi_duration = 0 } = frm.doc;
  if (loan_type === 'EMI' && emi_duration) {
    frm.set_value('recovery_amount', loan_principal / emi_duration);
  }
}

function calculate_monthly_interest(frm) {
  const { loan_type, loan_principal = 0, rate_of_interest = 0 } = frm.doc;
  if (loan_type === 'EMI') {
    frm.set_value(
      'monthly_interest',
      (loan_principal * rate_of_interest) / 100
    );
  }
}

function calculate_total_amount(frm) {
  const { loan_type, recovery_amount = 0, monthly_interest = 0 } = frm.doc;
  if (loan_type === 'EMI') {
    frm.set_value('total_amount', recovery_amount + monthly_interest);
  }
}

export default {
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
      frm.page.add_menu_item(__('New Loan Query'), async function() {
        const { message: service } = await frappe.call({
          method:
            'gwi_customization.microfinance.api.loanee.get_service_details',
          args: { customer: frm.doc['customer'] },
        });
        frappe.set_route('calculate_principal', {
          income: service['net_salary_amount'],
          end_date: service['date_of_retirement'],
          loan_plan: frm.doc['loan_plan'],
        });
      });
      const npa_dialog = new frappe.ui.Dialog({
        title: 'Set Loan as NPA',
        fields: [
          {
            fieldname: 'npa_date',
            label: 'NPA Date',
            fieldtype: 'Date',
            reqd: 1,
            default: frappe.datetime.get_today(),
          },
          {
            fieldname: 'final_amount',
            label: 'Final Amount',
            fieldtype: 'Currency',
            reqd: 1,
            default:
              frm.doc.__onload && frm.doc.__onload['outstanding_principal'],
          },
          {
            fieldname: 'remarks',
            label: 'Remarks (Optional)',
            fieldtype: 'Small Text',
          },
        ],
        primary_action: async function() {
          const values = npa_dialog.get_values();
          const { message: wo_amount } = await frappe.call({
            method: 'gwi_customization.microfinance.api.loan.set_npa',
            args: Object.assign({}, values, { loan: frm.doc['name'] }),
          });
          npa_dialog.hide();
          frm.reload_doc();
          if (wo_amount) {
            frappe.show_alert({
              message: `Wrote off ${fmt_money(wo_amount)}`,
              indicator: 'green',
            });
          }
        },
      });
      frm.page.add_menu_item(__('Set as NPA'), function() {
        npa_dialog.show();
      });
    }
  },
  render_chart: function(frm) {
    const chart_area = frm.$wrapper.find('.form-graph').removeClass('hidden');
    const chart = new frappe.Chart(chart_area[0], {
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
  loan_principal: function(frm) {
    calculate_recovery(frm);
    calculate_monthly_interest(frm);
  },
  rate_of_interest: calculate_monthly_interest,
  emi_duration: calculate_recovery,
  recovery_amount: calculate_total_amount,
  monthly_interest: calculate_total_amount,
};
