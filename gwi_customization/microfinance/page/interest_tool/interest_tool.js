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
  page.set_primary_action('Get Entries', async function() {
    const values = fg.get_values();
    console.log(values);
    if (values) {
      const { message: data } = await frappe.call({
        method: 'gwi_customization.microfinance.api.interest.list',
        args: values,
      });
      rh.removeClass('hidden').html(
        frappe.render_template('interest_list', {
          data: data.map(x => ({
            ...x,
            btn_label: x.status === 'Not Created' ? 'Make' : 'Edit',
            btn_type:
              x.status === 'Not Created' ? 'btn-default' : 'btn-warning',
          })),
        })
      );
      rh.find('button').click(e => {
        console.log(e.target.name);
      });
    }
  });
  page.set_secondary_action('Clear', function() {
    rh.empty().addClass('hidden');
    fg.set_values({ loan: null });
  });
};
