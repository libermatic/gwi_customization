# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries
from gwi_customization.microfinance.api.loan import get_outstanding_principal
from gwi_customization.microfinance.api.interest import make_name
from gwi_customization.microfinance.utils import calc_interest


class MicrofinanceLoanInterest(AccountsController):
    def autoname(self):
        self.name = make_name(self.loan, self.start_date)

    def before_save(self):
        if not self.billed_amount:
            outstanding_principal = get_outstanding_principal(
                self.loan, self.end_date
            )
            calculation_slab, rate_of_interest = frappe.get_value(
                'Microfinance Loan',
                self.loan,
                ['calculation_slab', 'rate_of_interest'],
            )
            self.billed_amount = calc_interest(
                outstanding_principal, rate_of_interest, calculation_slab
            )

    def on_update(self):
        self.update_status()

    def on_submit(self):
        self.make_gl_entries()

    def on_update_after_submit(self):
        self.update_status()

    def update_billed_amount(self, billed_amount):
        if self.paid_amount:
            return frappe.throw('Period already has amount paid')

        self.update({'billed_amount': billed_amount})
        self.save()

        interest_income_account = frappe.get_value(
            'Microfinance Loan', self.loan, 'interest_income_account'
        )
        cur_billed = frappe.db.sql(
            """
                SELECT SUM(credit - debit)
                FROM `tabGL Entry`
                WHERE account = '{account}' AND voucher_no = '{voucher_no}'
            """.format(
                account=interest_income_account,
                voucher_no=self.name,
            )
        )[0][0]
        if cur_billed != self.billed_amount:
            self.company = frappe.get_value(
                'Microfinance Loan', self.loan, 'company'
            )
            make_gl_entries(
                self.add_interest_gl_entries(self.billed_amount - cur_billed),
                merge_entries=False
            )

    def on_cancel(self):
        self.make_gl_entries(cancel=1)

    def get_gl_dict(self, args):
        gl_dict = frappe._dict({
            'against_voucher_type': 'Microfinance Loan',
            'against_voucher': self.loan,
        })
        gl_dict.update(args)
        return super(MicrofinanceLoanInterest, self).get_gl_dict(gl_dict)

    def make_gl_entries(self, cancel=0, adv_adj=0):
        self.company = frappe.get_value(
            'Microfinance Loan', self.loan, 'company'
        )
        gl_entries = self.add_interest_gl_entries(self.billed_amount)
        make_gl_entries(
            gl_entries, cancel=cancel, adv_adj=adv_adj, merge_entries=False
        )

    def add_interest_gl_entries(self, billed_amount, gle=[]):
        interest_income_account, loan_account = frappe.get_value(
            'Microfinance Loan',
            self.loan,
            ['interest_income_account', 'loan_account']
        )
        cost_center = frappe.db.get_value(
            'Microfinance Loan Settings', None, 'cost_center'
        )
        return gle + [
            self.get_gl_dict({
                'account': loan_account,
                'debit': billed_amount,
            }),
            self.get_gl_dict({
                'account': interest_income_account,
                'credit': billed_amount,
                'cost_center': cost_center,
                'remarks': 'Interest for {}'.format(self.period),
            }),
        ]

    def update_status(self, is_fined=False):
        current_status = self.status
        if is_fined:
            self.status = 'Fined'
        elif not self.paid_amount:
            self.status = 'Billed'
        elif self.paid_amount < self.billed_amount:
            self.status = 'Pending'
        elif self.paid_amount == self.billed_amount:
            self.status = 'Clear'
        if current_status != self.status:
            self.save()
