# -*- coding: utf-8 -*-
# Copyright (c) 2018, Libermatic and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import add_months, flt
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries, delete_gl_entries
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

    def before_submit(self):
        self.status = self.get_status()

    def on_submit(self):
        self.make_gl_entries()

    def before_update_after_submit(self):
        before = self.get_doc_before_save()
        if self.billed_amount != before.billed_amount:
            if self.paid_amount > self.billed_amount:
                frappe.throw('Paid amount cannot exceed billed amount')
            if before.fine_amount:
                frappe.throw('Period already has been fined')
            self.status = self.get_status()
        if self.paid_amount != before.paid_amount:
            if self.paid_amount > self.billed_amount:
                frappe.throw('Paid amount cannot exceed billed amount')
            if before.fine_amount:
                frappe.throw('Period already has been fined')
            self.status = self.get_status()
        if self.fine_amount != before.fine_amount:
            if self.paid_amount == self.billed_amount:
                frappe.throw('No unpaid amount to make late charges')
            if before.fine_amount:
                frappe.throw('Period has already been fined')
            if self.fine_amount > 0:
                self.status = 'Fined'

    def update_billed_amount(self, amount):
        self.billed_amount = amount
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
            delete_gl_entries(voucher_type=self.doctype, voucher_no=self.name)
            self.make_gl_entries()

    def set_fine_amount(self, amount=None):
        if amount:
            self.fine_amount = amount
        else:
            rate_of_late_charges = frappe.get_value(
                'Microfinance Loan', self.loan, 'rate_of_late_charges'
            )
            self.fine_amount = (self.billed_amount - flt(self.paid_amount)) \
                * flt(rate_of_late_charges) / 100
        self.save()
        self.make_gl_entries(is_fine=1)

    def on_cancel(self):
        self.make_gl_entries(cancel=1)

    def get_gl_dict(self, args):
        gl_dict = frappe._dict({
            'against_voucher_type': 'Microfinance Loan',
            'against_voucher': self.loan,
        })
        gl_dict.update(args)
        return super(MicrofinanceLoanInterest, self).get_gl_dict(gl_dict)

    def make_gl_entries(self, cancel=0, adv_adj=0, is_fine=0):
        self.company = frappe.get_value(
            'Microfinance Loan', self.loan, 'company'
        )
        if is_fine:
            self.posting_date = add_months(self.end_date, 1)
        interest_income_account, loan_account = frappe.get_value(
            'Microfinance Loan',
            self.loan,
            ['interest_income_account', 'loan_account']
        )
        cost_center = frappe.db.get_value(
            'Microfinance Loan Settings', None, 'cost_center'
        )
        amount = self.billed_amount if not is_fine else self.fine_amount
        remarks = 'Interest for {}' if not is_fine else 'Late charge for {}'
        gl_entries = [
            self.get_gl_dict({
                'account': loan_account,
                'debit': amount,
            }),
            self.get_gl_dict({
                'account': interest_income_account,
                'credit': amount,
                'cost_center': cost_center,
                'remarks': remarks.format(self.period),
            }),
        ]
        make_gl_entries(
            gl_entries, cancel=cancel, adv_adj=adv_adj, merge_entries=False
        )

    def get_status(self):
        if not self.paid_amount:
            return 'Billed'
        if self.paid_amount < self.billed_amount:
            return 'Pending'
        if self.paid_amount == self.billed_amount:
            return 'Clear'
