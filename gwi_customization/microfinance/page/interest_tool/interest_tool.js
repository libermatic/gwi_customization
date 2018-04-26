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
  const dialog = new frappe.ui.Dialog({
    fields: [
      {
        label: 'Amount',
        fieldname: 'billed_amount',
        fieldtype: 'Currency',
        description: 'Leave blank to calculate automagically',
      },
      {
        fieldname: 'unfine',
        fieldtype: 'Button',
        label: 'Remove Late Fine',
      },
      {
        fieldname: 'fine',
        fieldtype: 'Button',
        label: 'Make Late Fine',
      },
      { fieldtype: 'Column Break' },
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
  const dialog_btn_unfine = $(dialog.fields_dict['unfine'].wrapper)
    .find('button[data-fieldname="unfine"]')
    .removeClass('btn-xs')
    .addClass('btn-danger');
  const dialog_btn_fine = $(dialog.fields_dict['fine'].wrapper)
    .find('button[data-fieldname="fine"]')
    .removeClass('btn-xs')
    .addClass('btn-success');
  console.log(dialog);
  async function get_interests() {
    const values = fg.get_values();
    if (values) {
      rh.empty().addClass('hidden');
      const { message: data } = await frappe.call({
        method: 'gwi_customization.microfinance.api.interest.list',
        args: values,
      });
      rh
        .removeClass('hidden')
        .html(frappe.render_template('interest_list', { data }));
      data.forEach(({ name, status }) => {
        const btn = rh.find(`button[name='${name}']`);
        if (status == 'Unbilled') {
          btn.addClass('btn-info').text('Make');
        } else if (['Billed', 'Fined'].includes(status)) {
          btn.addClass('btn-warning').text('Edit');
        } else {
          btn.addClass('disabled').text('None');
        }
      });
      rh.find('button').on('click', function(e) {
        const { name, period, start_date, billed_amount, status } =
          data.find(({ name }) => name === e.target.name) || {};
        if (status === 'Unbilled') {
          dialog.set_title(`Create Interest for ${period}`);
        } else {
          dialog.set_title(`Edit Interest for ${period}`);
        }
        dialog_btn_unfine.toggleClass('hidden', status != 'Fined');
        dialog_btn_fine.toggleClass('hidden', status != 'Billed');
        dialog.set_values({ name, period, start_date, billed_amount, status });
        dialog.show();
      });
    }
  }

  function handle_fines(fieldname) {
    return async function() {
      const name = dialog.get_value('name');
      await frappe.call({
        method: `gwi_customization.microfinance.api.interest.${fieldname}`,
        args: { name },
      });
      dialog.hide();
      get_interests();
    };
  }

  page.set_primary_action('Get Entries', get_interests);
  page.set_secondary_action('Clear', function() {
    rh.empty().addClass('hidden');
    fg.set_values({ loan: null });
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
  dialog.fields_dict['unfine'].onclick(handle_fines('unfine'));
  dialog.fields_dict['fine'].onclick(handle_fines('fine'));
};
