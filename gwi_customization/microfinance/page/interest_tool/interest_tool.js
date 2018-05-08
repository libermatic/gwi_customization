frappe.pages['interest_tool'].on_page_load = function(wrapper) {
  const page = frappe.ui.make_app_page({
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
  fg.fields_dict['result_html'].$wrapper
    .css('overflow', 'auto')
    .addClass('hidden');
  wrapper.fg = fg;

  const dialog = new frappe.ui.Dialog({
    fields: [
      { fieldname: 'dialog_actions_html', fieldtype: 'HTML' },
      { fieldname: 'billed_amount', fieldtype: 'Data', hidden: 1 },
      { fieldname: 'name', fieldtype: 'Data', hidden: 1 },
      { fieldname: 'period', fieldtype: 'Data', hidden: 1 },
      { fieldname: 'start_date', fieldtype: 'Data', hidden: 1 },
    ],
  });

  const actions_by_status = {
    Unbilled: ['create'],
    Billed: ['update', 'remove', 'fine'],
    BilledFined: ['remove', 'unfine'],
    Pending: ['update', 'clear', 'fine'],
    Clear: [],
    Fined: ['unfine'],
    WroteOff: [],
  };
  const colors_by_status = {
    Unbilled: 'darkgrey',
    Billed: 'green',
    BilledFined: 'green',
    Pending: 'orange',
    Clear: 'blue',
    Fined: 'red',
    WroteOff: 'blue',
  };

  function render_buttons(status) {
    const dialog_actions_html = $(
      frappe.render_template('interest_tool_dialog_actions')
    );
    actions_by_status[status].forEach(action => {
      dialog_actions_html
        .find(`tr[data-name="${action}"]`)
        .removeClass('text-muted')
        .find('button')
        .removeClass('disabled')
        .addClass('btn-info');
    });
    return dialog_actions_html.prop('outerHTML');
  }

  function make_action(action) {
    return async function() {
      try {
        await action();
        get_interests();
      } finally {
        dialog.hide();
      }
    };
  }
  function handle_action(fieldname) {
    return async function() {
      return await frappe.call({
        method: `gwi_customization.microfinance.api.interest.${fieldname}`,
        args: { name: dialog.get_value('name') },
      });
    };
  }

  function prompt_promisified(default_value = null) {
    return new Promise((resolve, reject) =>
      frappe.prompt(
        [
          {
            fieldname: 'value',
            fieldtype: 'Currency',
            label: 'Enter amount',
            default: default_value,
            description: 'Leave as it is to calculate automagically',
          },
        ],
        ({ value }) => resolve(value),
        'Interest Amount',
        'Submit'
      )
    );
  }

  const requests = {
    create: async function() {
      const loan = fg.get_value('loan');
      const { period, start_date } = dialog.get_values();
      const billed_amount = await prompt_promisified();
      return await frappe.call({
        method: 'gwi_customization.microfinance.api.interest.create',
        args: { loan, period, start_date, billed_amount },
      });
    },
    update: async function() {
      const name = dialog.get_value('name');
      const billed_amount = await prompt_promisified(
        dialog.get_value('billed_amount')
      );
      return await frappe.call({
        method: 'gwi_customization.microfinance.api.interest.edit',
        args: { name, billed_amount },
      });
    },
    clear: handle_action('clear'),
    remove: handle_action('remove'),
    fine: handle_action('fine'),
    unfine: handle_action('unfine'),
  };

  async function get_interests() {
    const values = fg.get_values();
    if (values) {
      const result_html = $(fg.fields_dict['result_html'].wrapper)
        .empty()
        .addClass('hidden');
      const [{ message: data }, { message: loan }] = await Promise.all([
        frappe.call({
          method: 'gwi_customization.microfinance.api.interest.list',
          args: values,
        }),
        frappe.db.get_value('Microfinance Loan', values['loan'], [
          'customer_name',
          'loan_plan',
        ]),
      ]);
      result_html.removeClass('hidden').html(
        frappe.render_template('interest_list', {
          loan,
          data: data.map(x => ({
            indicator: colors_by_status[x.status],
            ...x,
          })),
        })
      );
      data.forEach(({ name, status, fine_wrote_off }) => {
        const btn = result_html.find(`button[name='${name}']`);
        if (status === 'Clear' || fine_wrote_off) {
          btn.addClass('disabled').text('None');
        }
      });
      result_html.find('button').on('click', async function(e) {
        const {
          name,
          period,
          start_date,
          billed_amount,
          outstanding_amount,
          fine_wrote_off,
          status,
        } =
          data.find(({ name }) => name === e.target.name) || {};
        dialog.set_title(`Actions for Interest Entry ${period}`);
        let render_status = status;
        if (status === 'Fined') {
          if (billed_amount === outstanding_amount) {
            render_status = 'BilledFined';
          }
          if (fine_wrote_off) {
            render_status = 'WroteOff';
          }
        }
        dialog.fields_dict['dialog_actions_html'].html(
          render_buttons(render_status)
        );
        actions_by_status[render_status].forEach(action => {
          dialog.fields_dict['dialog_actions_html'].$wrapper
            .find(`tr[data-name="${action}"] button`)
            .click(make_action(requests[action]));
        });
        dialog.set_values({ name, period, start_date, billed_amount });
        dialog.show();
      });
    }
  }

  page.set_primary_action('Get Entries', get_interests);
  page.set_secondary_action('Clear', function() {
    fg.fields_dict['result_html'].$wrapper.empty().addClass('hidden');
    fg.set_values({ loan: null });
  });
};

frappe.pages['interest_tool'].refresh = function({ fg }) {
  if (frappe.route_options && frappe.route_options['loan']) {
    fg.set_value('loan', frappe.route_options['loan']);
    fg.fields_dict['result_html'].$wrapper.empty().addClass('hidden');
  }
};
