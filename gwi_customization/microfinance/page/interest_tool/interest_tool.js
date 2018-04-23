frappe.pages['interest_tool'].on_page_load = function(wrapper) {
  var page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'Interests and Charges',
    single_column: true,
  });
  const fg = new frappe.ui.FieldGroup({
    fields: [
      {
        label: 'Loan',
        fieldtype: 'Link',
        options: 'Microfinance Loan',
        reqd: 1,
      },
      { fieldtype: 'Column Break' },
      {
        label: 'From Date',
        fieldtype: 'Date',
        default: frappe.datetime.year_start(),
        reqd: 1,
      },
      { fieldtype: 'Column Break' },
      {
        label: 'To Date',
        fieldtype: 'Date',
        default: frappe.datetime.year_end(),
        reqd: 1,
      },
      { fieldname: 'result_section', fieldtype: 'Section Break' },
      { fieldname: 'result_html', fieldtype: 'HTML' },
    ],
    parent: page.body,
  });
  fg.make();
  const rh = $(fg.fields_dict['result_html'].wrapper);
  rh.css('overflow', 'auto').addClass('hidden');
  async function get_interests() {
    const values = fg.get_values();
    if (values) {
      rh.empty().addClass('hidden');
      const { message: data } = await frappe.call({
        method: 'gwi_customization.microfinance.api.interest.list',
        args: values,
      });
      console.log(data);
      rh
        .removeClass('hidden')
        .html(frappe.render_template('interest_list', { data }));
      data.forEach(({ name, status }) => {
        const btn = rh.find(`button[name='${name}']`);
        if (status == 'Unbilled') {
          btn.addClass('btn-info').text('Make');
        } else if (status == 'Billed') {
          btn.addClass('btn-warning').text('Edit');
        } else {
          btn.addClass('disabled').text('None');
        }
      });
      rh.find('button').click(e => {
        const { name, period, start_date, billed_amount, status } =
          data.find(({ name }) => name === e.target.name) || {};
        if (status === 'Unbilled') {
          dialog.set_title(`Create Interest for ${period}`);
        } else {
          dialog.set_title(`Edit Interest for ${period}`);
        }
        dialog.set_values({ name, period, start_date, billed_amount, status });
        dialog.show();
      });
    }
  }
  page.set_primary_action('Get Entries', get_interests);
  page.set_secondary_action('Clear', function() {
    rh.empty().addClass('hidden');
    fg.set_values({ loan: null });
  });
  const dialog = new frappe.ui.Dialog({
    fields: [
      {
        label: 'Amount',
        fieldname: 'billed_amount',
        fieldtype: 'Currency',
        description: 'Leave blank to calculate automagically',
      },
      {
        fieldname: 'name',
        fieldtype: 'Link',
        options: 'Microfinance Loan Interest',
        hidden: 1,
      },
      { fieldname: 'period', fieldtype: 'Data', hidden: 1 },
      { fieldname: 'start_date', fieldtype: 'Data', hidden: 1 },
      { fieldname: 'status', fieldtype: 'Data', hidden: 1 },
    ],
  });
  dialog.set_primary_action('Submit', async function({
    name,
    period,
    start_date,
    billed_amount,
    status,
  }) {
    if (status === 'Unbilled') {
      const loan = fg.get_value('loan');
      await frappe.call({
        method: 'gwi_customization.microfinance.api.interest.create',
        args: { loan, period, start_date, billed_amount },
      });
    } else {
      await frappe.call({
        method: 'gwi_customization.microfinance.api.interest.edit',
        args: { name, billed_amount },
      });
    }
    dialog.hide();
    get_interests();
  });
};
