frappe.pages['calculate_principal'].on_page_load = function(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'Calculate Principal and Interests',
    single_column: true,
  });
  const fg = new frappe.ui.FieldGroup({
    fields: [
      { label: 'Income', fieldtype: 'Currency', reqd: 1 },
      { fieldtype: 'Column Break' },
      {
        label: 'Date of Retirement',
        fieldname: 'end_date',
        fieldtype: 'Date',
        reqd: 1,
      },
      { fieldtype: 'Column Break' },
      {
        label: 'Loan Plan',
        fieldtype: 'Link',
        options: 'Microfinance Loan Plan',
        reqd: 1,
      },
      { fieldname: 'result_section', fieldtype: 'Section Break' },
      { fieldname: 'result_html', fieldtype: 'HTML' },
    ],
    parent: page.body,
  });
  fg.make();
  wrapper.fg = fg;
  const rh = $(fg.fields_dict['result_html'].wrapper);
  rh.css('overflow', 'auto').addClass('hidden');
  page.set_primary_action('Calculate', async function() {
    const values = fg.get_values();
    if (values) {
      const { message: data } = await frappe.call({
        method: 'gwi_customization.microfinance.api.loan.calculate_principal',
        args: { ...values, execution_date: frappe.datetime.nowdate() },
      });
      rh
        .removeClass('hidden')
        .html(frappe.render_template('calculate_principal', data));
    }
  });
  page.set_secondary_action('Reset', function() {
    rh.empty().addClass('hidden');
    fg.set_values({ income: null, end_date: null, loan_plan: null });
  });
  frappe.breadcrumbs.add('Microfinance');
};

frappe.pages['calculate_principal'].refresh = function({ fg }) {
  if (frappe.route_options) {
    const { income, end_date, loan_plan } = frappe.route_options;
    fg.set_value('income', income);
    fg.set_value('end_date', end_date);
    fg.set_value('loan_plan', loan_plan);
  }
};
