import Vue from 'vue/dist/vue.js';
import * as R from 'ramda'

import AuditStatementSummary from '../vue/AuditStatementSummary.vue';

const sumBy = R.compose(
  R.reduce((a, x) => a + (x ?? 0), 0),
  R.pluck
);

function set_balance(frm, cdt, cdn) {
  const { idx = 0, principal = 0 } = frappe.get_doc(cdt, cdn);
  const { balance: prev_balance = 0 } =
    (frm.doc.transactions || []).find((row) => row.idx === idx - 1) || {};
  frappe.model.set_value(cdt, cdn, 'balance', prev_balance - principal);
}

function get_slabbed_amount(amount, slab) {
  if (slab) {
    return Math.ceil(flt(amount) / slab) * slab;
  }
  return flt(amount);
}

function set_interest(frm, cdt, cdn) {
  const { interest_rate = 0, calculation_slab = 0 } = frm.doc;
  const { idx = 0 } = frappe.get_doc(cdt, cdn);
  const { balance: prev_balance = 0 } =
    (frm.doc.transactions || []).find((row) => row.idx === idx - 1) || {};
  const slabbed_balance = get_slabbed_amount(prev_balance, calculation_slab);
  frappe.model.set_value(
    cdt,
    cdn,
    'interest',
    (slabbed_balance * interest_rate) / 100
  );
}

function set_period(frm, cdt, cdn) {
  const { period_date } = frappe.get_doc(cdt, cdn);
  frappe.model.set_value(
    cdt,
    cdn,
    'period',
    moment(period_date).format('MMMM, YYYY')
  );
}

function render_dashboard(frm) {
  const { balance = 0 } = R.last(frm.doc.transactions) || {};
  const principals = sumBy(frm.doc.transactions, 'principal');
  const interests = sumBy(frm.doc.transactions, 'interest');
  const node = frm.dashboard.add_section('<div />').children()[0];
  new Vue({
    el: node,
    render: (h) =>
      h(AuditStatementSummary, {
        props: { principals, interests, balance, formatter: format_currency },
      }),
  });
  frm.dashboard.show();
}

const audit_statement_detail = {
  transactions_add: set_interest,
  period_date: set_period,
  principal: set_balance,
  interest: set_balance,
};

export default {
  audit_statement_detail,
  refresh: function (frm) {
    if (!frm.doc.__islocal) {
      render_dashboard(frm);
    }
  },
};
